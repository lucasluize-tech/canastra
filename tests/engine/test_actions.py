from __future__ import annotations

from uuid import uuid4

from canastra.domain.cards import HEARTS, SPADES, Card
from canastra.engine.actions import (
    Action,
    Chin,
    CreateMeld,
    Discard,
    Draw,
    ExtendMeld,
    PickUpTrash,
)
from canastra.engine.events import (
    CardDrawn,
    Chinned,
    DeckReplenished,
    Discarded,
    Event,
    GameEnded,
    MeldCreated,
    MeldExtended,
    ReserveTaken,
    TrashPickedUp,
    TurnAdvanced,
)


def test_all_action_types_serialize():
    actions: list[Action] = [
        Draw(player_id=0),
        PickUpTrash(player_id=0),
        CreateMeld(player_id=0, cards=[Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]),
        ExtendMeld(player_id=0, meld_id=uuid4(), cards=[Card(HEARTS, 6)]),
        Discard(player_id=0, card=Card(HEARTS, 3)),
        Chin(player_id=0),
    ]
    for a in actions:
        blob = a.model_dump_json()
        a2 = a.__class__.model_validate_json(blob)
        assert a2 == a


def test_all_event_types_construct():
    events: list[Event] = [
        CardDrawn(player_id=0, card=Card(HEARTS, 3)),
        TrashPickedUp(player_id=0, cards=[Card(HEARTS, 3)]),
        MeldCreated(player_id=0, team_id=0, meld_id=uuid4(), cards=[Card(HEARTS, 3)]),
        MeldExtended(player_id=0, team_id=0, meld_id=uuid4(), added=[Card(HEARTS, 6)]),
        Discarded(player_id=0, card=Card(HEARTS, 3)),
        ReserveTaken(player_id=0, team_id=0, reserves_remaining=1),
        DeckReplenished(team_id=0, cards_added=11),
        TurnAdvanced(next_player_id=1),
        Chinned(team_id=0),
        GameEnded(winning_team=0, scores={0: 1100, 1: 200}),
    ]
    for e in events:
        assert e.model_dump_json()


import pytest

from canastra.engine.engine import apply
from canastra.engine.errors import ActionRejected
from canastra.engine.setup import initial_state
from canastra.engine.state import Phase


def test_draw_in_waiting_draw_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    assert len(s.hands[0]) == 11
    top_card = s.deck[-1]

    s1, events = apply(s, Draw(player_id=0))
    assert len(s1.hands[0]) == 12
    assert s1.hands[0][-1] == top_card
    assert len(s1.deck) == len(s.deck) - 1
    assert s1.phase is Phase.PLAYING
    assert s1.current_turn.phase is Phase.PLAYING
    assert s1.action_seq == s.action_seq + 1
    assert len(events) == 1
    assert isinstance(events[0], CardDrawn)
    assert events[0].player_id == 0
    assert events[0].card == top_card


def test_draw_wrong_player_rejected(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="not your turn"):
        apply(s, Draw(player_id=1))


def test_draw_wrong_phase_rejected(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s1, _ = apply(s, Draw(player_id=0))
    with pytest.raises(ActionRejected, match="phase"):
        apply(s1, Draw(player_id=0))


def test_pickup_trash_takes_whole_pile(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    trash = [Card(HEARTS, 5), Card(HEARTS, 6), Card(HEARTS, 7)]
    s = s.model_copy(update={"trash": trash})

    s1, events = apply(s, PickUpTrash(player_id=0))
    assert s1.trash == []
    assert len(s1.hands[0]) == 11 + 3
    assert s1.hands[0][-3:] == trash
    assert s1.phase is Phase.PLAYING
    assert len(events) == 1
    assert isinstance(events[0], TrashPickedUp)
    assert events[0].cards == trash


def test_pickup_trash_rejects_empty(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="empty"):
        apply(s, PickUpTrash(player_id=0))


def test_pickup_trash_wrong_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = s.model_copy(update={"trash": [Card(HEARTS, 5)]})
    s1, _ = apply(s, PickUpTrash(player_id=0))
    with pytest.raises(ActionRejected, match="phase"):
        apply(s1, PickUpTrash(player_id=0))


def _hand_with(s, pid, cards):
    """Prepend `cards` to pid's hand (for deterministic meld tests)."""
    new_hands = dict(s.hands)
    new_hands[pid] = list(cards) + new_hands[pid]
    return s.model_copy(update={"hands": new_hands})


def _advance_to_playing(s, pid=0):
    s, _ = apply(s, Draw(player_id=pid))
    return s


def test_create_meld_valid(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    meld_cards = [Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]
    s = _hand_with(s, 0, meld_cards)
    s = _advance_to_playing(s)

    s1, events = apply(s, CreateMeld(player_id=0, cards=meld_cards))
    assert len(s1.melds[0]) == 1
    assert s1.melds[0][0].cards == meld_cards
    assert s1.melds[0][0].permanent_dirty is False
    for c in meld_cards:
        assert s1.hands[0].count(c) == s.hands[0].count(c) - 1
    assert len(events) == 1
    assert isinstance(events[0], MeldCreated)


def test_create_meld_too_short(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    meld_cards = [Card(HEARTS, 3), Card(HEARTS, 4)]
    s = _hand_with(s, 0, meld_cards)
    s = _advance_to_playing(s)
    with pytest.raises(ActionRejected, match="valid"):
        apply(s, CreateMeld(player_id=0, cards=meld_cards))


def test_create_meld_not_in_order(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    meld_cards = [Card(HEARTS, 3), Card(SPADES, 4), Card(HEARTS, 5)]
    s = _hand_with(s, 0, meld_cards)
    s = _advance_to_playing(s)
    with pytest.raises(ActionRejected, match="valid"):
        apply(s, CreateMeld(player_id=0, cards=meld_cards))


def test_create_meld_cards_not_in_hand(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = _advance_to_playing(s)
    fake = [Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]
    # Force: clear hand so the "fake" cards are definitely not present
    s = s.model_copy(update={"hands": {**s.hands, 0: []}})
    with pytest.raises(ActionRejected, match="hand"):
        apply(s, CreateMeld(player_id=0, cards=fake))


def test_create_meld_wrong_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="phase"):
        apply(s, CreateMeld(player_id=0, cards=[Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]))


# ---------------------------------------------------------------------------
# ExtendMeld tests
# ---------------------------------------------------------------------------


def test_extend_meld_valid(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    base = [Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]
    s = _hand_with(s, 0, base + [Card(HEARTS, 6)])
    s = _advance_to_playing(s)
    s, _ = apply(s, CreateMeld(player_id=0, cards=base))
    meld_id = s.melds[0][0].id

    s1, events = apply(s, ExtendMeld(player_id=0, meld_id=meld_id, cards=[Card(HEARTS, 6)]))
    assert s1.melds[0][0].cards[-1] == Card(HEARTS, 6)
    assert len(s1.melds[0][0].cards) == 4
    assert s1.hands[0].count(Card(HEARTS, 6)) == s.hands[0].count(Card(HEARTS, 6)) - 1
    assert len(events) == 1
    assert isinstance(events[0], MeldExtended)


def test_extend_meld_rejects_break_run(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    base = [Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]
    s = _hand_with(s, 0, base + [Card(HEARTS, 10)])
    s = _advance_to_playing(s)
    s, _ = apply(s, CreateMeld(player_id=0, cards=base))
    meld_id = s.melds[0][0].id

    with pytest.raises(ActionRejected, match="extend"):
        apply(s, ExtendMeld(player_id=0, meld_id=meld_id, cards=[Card(HEARTS, 10)]))


def test_extend_meld_unknown_id(cfg_4p2d):
    from uuid import uuid4

    s = initial_state(cfg_4p2d)
    s = _hand_with(s, 0, [Card(HEARTS, 6)])
    s = _advance_to_playing(s)
    with pytest.raises(ActionRejected, match="meld"):
        apply(s, ExtendMeld(player_id=0, meld_id=uuid4(), cards=[Card(HEARTS, 6)]))


def test_extend_meld_cards_not_in_hand(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    base = [Card(HEARTS, 3), Card(HEARTS, 4), Card(HEARTS, 5)]
    s = _hand_with(s, 0, base)
    s = _advance_to_playing(s)
    s, _ = apply(s, CreateMeld(player_id=0, cards=base))
    meld_id = s.melds[0][0].id

    s = s.model_copy(update={"hands": {**s.hands, 0: []}})
    with pytest.raises(ActionRejected, match="hand"):
        apply(s, ExtendMeld(player_id=0, meld_id=meld_id, cards=[Card(HEARTS, 6)]))


def test_extend_meld_sets_permanent_dirty(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    # Base: [AceH, 2H, 3H] — valid clean 3-card run (Ace-low, natural-2, 3).
    # Extend with off-suit 2S: combined [AceH, 2H, 3H, 2S] has matching-suit-2
    # (2H) + another 2 (2S), triggering permanent_dirty via Condition 2.
    base = [Card(HEARTS, "Ace"), Card(HEARTS, 2), Card(HEARTS, 3)]
    s = _hand_with(s, 0, base + [Card(SPADES, 2)])
    s = _advance_to_playing(s)
    s, _ = apply(s, CreateMeld(player_id=0, cards=base))
    meld_id = s.melds[0][0].id

    s1, _ = apply(s, ExtendMeld(player_id=0, meld_id=meld_id, cards=[Card(SPADES, 2)]))
    assert s1.melds[0][0].permanent_dirty is True


# ---------------------------------------------------------------------------
# Discard tests
# ---------------------------------------------------------------------------


def test_discard_advances_turn(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = _advance_to_playing(s)
    discard_card = s.hands[0][0]

    s1, events = apply(s, Discard(player_id=0, card=discard_card))
    assert s1.trash[-1] == discard_card
    assert (
        discard_card not in s1.hands[0]
        or s1.hands[0].count(discard_card) == s.hands[0].count(discard_card) - 1
    )
    assert s1.current_turn.player_id == 1
    assert s1.current_turn.phase is Phase.WAITING_DRAW
    assert s1.phase is Phase.WAITING_DRAW
    # Events: Discarded, TurnAdvanced
    assert any(isinstance(e, Discarded) for e in events)
    assert any(isinstance(e, TurnAdvanced) for e in events)


def test_discard_wrong_phase(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    with pytest.raises(ActionRejected, match="phase"):
        apply(s, Discard(player_id=0, card=Card(HEARTS, 3)))


def test_discard_card_not_in_hand(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    s = _advance_to_playing(s)
    s = s.model_copy(update={"hands": {**s.hands, 0: []}})
    with pytest.raises(ActionRejected, match="hand"):
        apply(s, Discard(player_id=0, card=Card(HEARTS, 3)))


def test_discard_turn_wraps(cfg_4p2d):
    s = initial_state(cfg_4p2d)
    for pid in range(4):
        s, _ = apply(s, Draw(player_id=pid))
        s, _ = apply(s, Discard(player_id=pid, card=s.hands[pid][0]))
    assert s.current_turn.player_id == 0
