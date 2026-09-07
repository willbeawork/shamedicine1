import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# ============================================================
# SHAMEDICINE - Native Streamlit UI
# ============================================================

GAME_CONFIG = {
    "tiles": [
        {"name": "START", "type": "start"},
        {"name": "DESCRIBE", "type": "describe"},
        {"name": "ACT", "type": "act"},
        {"name": "DESCRIBE", "type": "describe"},
        {"name": "ACT", "type": "act"},
        {"name": "DESCRIBE", "type": "describe"},
        {"name": "ACT", "type": "act"},
        {"name": "DESCRcribe", "type": "describe"},
        {"name": "ACT", "type": "act"},
        {"name": "FINISH", "type": "finish"},
    ],
    "timer_seconds": 45,
    "csv_files": {
        "describe": "describe_terms.csv",
        "act": "act_terms.csv",
    },
}

DEFAULT_STATE = {
    "game_started": False,
    "current_player": 1,
    "p1_position": 0,
    "p2_position": 0,
    "game_history": [],
    "terms_cache": {},
    "current_card": None,
    "current_category": None,
    "cards_shown": 0,
    "timer_active": False,
    "timer_started_at": None,
    "winner": None,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


def load_terms(category):
    if category in st.session_state.terms_cache:
        return st.session_state.terms_cache[category]

    filename = GAME_CONFIG["csv_files"][category]

    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        st.error(f"Could not find `{filename}`.")
        return []

    if df.empty:
        st.error(f"`{filename}` is empty.")
        return []

    column = df.columns[0]
    terms = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    terms = [term for term in terms if term]

    st.session_state.terms_cache[category] = terms
    return terms


def get_current_category():
    position = (
        st.session_state.p1_position
        if st.session_state.current_player == 1
        else st.session_state.p2_position
    )
    return ["describe", "act"][position % 2]


def draw_card():
    """Draw a card WITHOUT touching the timer."""
    category = get_current_category()
    terms = load_terms(category)

    if not terms:
        return

    st.session_state.current_category = category
    st.session_state.current_card = random.choice(terms)
    st.session_state.cards_shown += 1


def next_card_with_score():
    """Next Card adds 1 point but DOES NOT switch player or restart timer."""
    if st.session_state.current_player == 1:
        st.session_state.p1_position += 1
        player_name = st.session_state.player1_name
    else:
        st.session_state.p2_position += 1
        player_name = st.session_state.player2_name

    st.session_state.game_history.append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "player": player_name,
            "card": st.session_state.current_card,
            "category": st.session_state.current_category,
            "score": 1,
        }
    )

    # Check for winner
    if st.session_state.p1_position >= st.session_state.points_to_win:
        st.session_state.winner = st.session_state.player1_name
        st.session_state.game_started = False
        return

    if st.session_state.p2_position >= st.session_state.points_to_win:
        st.session_state.winner = st.session_state.player2_name
        st.session_state.game_started = False
        return

    draw_card()


def skip_card():
    """Skip card without scoring; DO NOT switch player or restart timer."""
    draw_card()


def start_game():
    st.session_state.game_started = True
    st.session_state.current_player = 1
    st.session_state.p1_position = 0
    st.session_state.p2_position = 0
    st.session_state.game_history = []
    st.session_state.current_card = None
    st.session_state.current_category = None
    st.session_state.cards_shown = 0
    st.session_state.winner = None

    # Start timer ONCE per turn
    st.session_state.timer_active = True
    st.session_state.timer_started_at = time.time()

    draw_card()


def reset_game():
    for key, value in DEFAULT_STATE.items():
        if isinstance(value, list):
            st.session_state[key] = []
        elif isinstance(value, dict):
            st.session_state[key] = {}
        else:
            st.session_state[key] = value


def remaining_seconds():
    if not st.session_state.timer_active or not st.session_state.timer_started_at:
        return GAME_CONFIG["timer_seconds"]

    elapsed = int(time.time() - st.session_state.timer_started_at)
    return max(0, GAME_CONFIG["timer_seconds"] - elapsed)


@st.fragment(run_every="1s")
def draw_timer():
    seconds = remaining_seconds()

    if st.session_state.timer_active and seconds <= 0:
        st.session_state.timer_active = False
        st.session_state.timer_started_at = None
        st.error("⏰ Time's up!")

        # SWITCH PLAYER ONLY WHEN TIMER ENDS
        st.session_state.current_player = (
            2 if st.session_state.current_player == 1 else 1
        )

        # Start new timer for new player
        st.session_state.timer_active = True
        st.session_state.timer_started_at = time.time()

        # Draw first card of new turn
        draw_card()

    elif seconds <= 10:
        st.warning(f"⏱️ **{seconds} seconds remaining**")
    else:
        st.metric("Time remaining", f"{seconds} seconds")


def draw_race():
    target = st.session_state.points_to_win
    p1 = min(st.session_state.p1_position, target)
    p2 = min(st.session_state.p2_position, target)

    st.subheader("🏁 Race to Finish")

    def race_line(position):
        track_length = 40  # BIGGER TRACK
        marker = min(track_length - 1, round((position / target) * (track_length - 1)))

        track = ["·"] * track_length
        track[marker] = "🏃‍♂️"  # BIGGER RUNNER
        track[-1] = "🏁"        # BIGGER FINISH
        return "".join(track)

    st.markdown(f"**{st.session_state.player1_name}**")
    st.markdown(race_line(p1))
    st.caption(f"{p1} / {target} points")

    st.markdown(f"**{st.session_state.player2_name}**")
    st.markdown(race_line(p2))
    st.caption(f"{p2} / {target} points")


def draw_history():
    if not st.session_state.game_history:
        return

    with st.expander("Game History"):
        st.dataframe(
            pd.DataFrame(st.session_state.game_history),
            use_container_width=True,
            hide_index=True,
        )


st.set_page_config(
    page_title="Shamedicine",
    page_icon="🩺",
    layout="wide",
)

# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🩺 Shamedicine")
st.sidebar.caption("A medical revision game")
st.sidebar.divider()

player1 = st.sidebar.text_input(
    "Player 1",
    value=st.session_state.get("player1_name", "Player 1"),
)
player2 = st.sidebar.text_input(
    "Player 2",
    value=st.session_state.get("player2_name", "Player 2"),
)
points_to_win = st.sidebar.slider(
    "Points to win",
    min_value=3,
    max_value=20,
    value=st.session_state.get("points_to_win", 10),
)

st.session_state.player1_name = player1
st.session_state.player2_name = player2
st.session_state.points_to_win = points_to_win

if st.sidebar.button("Start New Game", type="primary", use_container_width=True):
    start_game()
    st.rerun()

if st.sidebar.button("Reset Game", use_container_width=True):
    reset_game()
    st.rerun()

# ============================================================
# MAIN
# ============================================================

st.title("🩺 Shamedicine")
st.caption("Describe it. Act it. Don't say the word.")

if st.session_state.winner:
    st.success(f"🏆 {st.session_state.winner} wins!")
    st.info("Start a new game from the sidebar to play again.")

elif not st.session_state.game_started:
    st.info("Set the players and points to win, then click Start New Game.")

    st.subheader("How to play")
    st.markdown(
        """
        1. The active player gets a medical term.
        2. Depending on the round, **Describe** or **Act** the term.
        3. Click **Next Card** to earn 1 point.
        4. Click **Skip Card** to pass without earning a point.
        5. The player switches ONLY when the timer ends.
        """
    )

else:
    current_player_name = (
        st.session_state.player1_name
        if st.session_state.current_player == 1
        else st.session_state.player2_name
    )

    st.subheader(f"🎯 {current_player_name}'s turn")

    card_col, controls_col = st.columns([2.4, 1], gap="large")

    with card_col:
        with st.container(border=True):
            category = (
                st.session_state.current_category
                or get_current_category()
            )

            st.caption(category.upper())

            if st.session_state.current_card:
                st.header(st.session_state.current_card)
            else:
                st.info("Click Next Card to get a term.")

    with controls_col:
        st.subheader("Card Controls")

        if st.button("🟢 Next Card", type="primary", use_container_width=True):
            next_card_with_score()
            st.rerun()

        if st.button("🔴 Skip Card", use_container_width=True):
            skip_card()
            st.rerun()

        st.divider()

        draw_timer()

        st.caption("The 45-second timer starts when the turn begins.")

    st.divider()
    draw_race()

    draw_history()
