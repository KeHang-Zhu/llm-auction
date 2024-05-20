import textwrap
from edsl import QuestionMultipleChoice, Scenario

def run_game(option1, option2, pay_offs, rounds):
    instructions = textwrap.dedent("""
        You are playing a game with another player and you want to win.
        You can choose to play either {{option1}} or {{option2}}.
        The payoffs are as follows: {{pay_offs}}.
    """)

    history = []
    player_1_total, player_2_total = 0, 0
    for round in range(1, rounds + 1):
        print("Now starting round", round)
        scenarios = [Scenario({'player': "player 1", "history": history}), Scenario({'player': "player 2", "history": history})]
        q = QuestionMultipleChoice(question_text = instructions + """You are player {{player}}. The history of the game so far, if any is: {{history}}""",
                                   question_options = [option1, option2], question_name = "choice")

        results = q.by(scenarios).run()
        player_1_choice, player_2_choice = list(results.select('answer.*')[0].values())[0]
        pay_off = pay_offs[(player_1_choice, player_2_choice)]
        outcome = f"""In round {round}, player 1 chose {player_1_choice} and player 2 chose {player_2_choice}.
Player 1's payoff is {pay_off[0]} and player 2's payoff is {pay_off[1]}."""
        player_1_total += pay_off[0]
        player_2_total += pay_off[1]
        print(outcome)
        history.append(outcome)

    print(f"Player 1's total payoff is {player_1_total} and player 2's total payoff is {player_2_total}.")

if __name__ == "__main__":
    option1 = "hunt"
    option2 = "gather"
    pay_offs = {
        (f'{option1}', f'{option1}'): (1, -1),
        (f'{option1}', f'{option2}'): (-1, 1),
        (f'{option2}', f'{option1}'): (1, -1),
        (f'{option2}', f'{option2}'): (-1, 1)
    }
    rounds = 10
    run_game(option1, option2, pay_offs, rounds)