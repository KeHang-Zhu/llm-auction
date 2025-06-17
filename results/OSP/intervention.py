from edsl.questions import QuestionMultipleChoice, QuestionLinearScale, QuestionTopK, QuestionYesNo, QuestionNumerical
from edsl import Survey
from edsl.surveys import Survey
from concurrent.futures import ProcessPoolExecutor, as_completed
from edsl import Cache
from edsl import Model
import traceback

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import sys

load_dotenv()

Bidders = ["Bidder 0", "Bidder 1", "Bidder 2"]

Rules_ACB = "In this game, you will bid in an auction for a money prize. The prize may have a different dollar value for each person in your group. \nYou will play this game for 10 round. All dollar amounts in this game are in 1 dollar increments.\nAt the start of each round, we display your value for this round\u2019s prize. If you win the prize, you will earn the value of the prize, minus any payments from the auction. Your value for the prize will be calculated as follows: \nAt the start of each round, we display your value for this round\u2019s prize. If you win the prize, you will earn the value of the prize, minus any payments from the auction. Your value for the prize will be calculated as follows: \n1. For each group we will draw a common value, which will be between 10 and 20. Every number between 10 and 20 is equally likely to be drawn. \n2. For each person, we will also draw a private adjustment, which will be between 0 and 20. Every number between 0 and 20 is equally likely to be drawn.\nAt the start of each round, you will learn your total value for the prize, but not the common value or the private adjustment. This means that each person in your group may have a different value for the prize. However, when you have a high value, it is more likely that other people in your group have a high value. The auction proceeds as follows: First, you will learn your value for the prize. Then, the auction will start. We will display a price to everyone in your group, that starts low and counts upwards in 1 USD increments, up to a maximum of 40. At any point, you can choose to leave the auction. The starting bidding will be 10.\nWhen there is only one bidder left in the auction, that bidder will win the prize at the current price. This means that we will add to her earnings her value for the prize, and subtract from her earnings the current price. All other bidders's earnings will not change. At the end of each auction, we will show you the prices where bidders stopped, and the winning bidder\u2019s profits. If there is a tie for the highest bidder, no bidder will win the object."


Persona = "'goal': You need to maximize your profits. If you win the bid, your profit is your value for the prize subtracting by your final bid. If you don't win, your profit is 0."

def Intervenetion_ACB(player, reasoning, current_price, value, remaining_bidders, c):
    
    other_bidders = [bidder for bidder in Bidders if bidder != player]
    name = f"You are {player}. You are bidding with {' and '.join(other_bidders)}."
    
    RULES = name + Rules_ACB + Persona
    question_text0_0 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    The current price is {current_price}.
    Your previous decision is to drop out. Your reason for that is {reasoning}.
    Give it a second thought. Do you want to drop out?
    '''
    
    question_text1_0 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    The current price is {current_price}.
    Your previous decision is to drop out. Your reason for that is {reasoning}.
    Now there is additional information that at this stage, {remaining_bidders} bidders are still on the table for this auction.    
    Give it a second thought. Do you want to drop out?
    '''
    
    question_text2_0 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    The current price is {current_price}.
    Your previous decision is to drop out. Your reason for that is {reasoning}.
    Now there is additional advice: Remember to be a profit maximizer and not to be afraid of risk -- a 50/50 gamble between $110 and $0 is more valuable than guaranteed $50.
    Give it a second thought. Do you want to drop out?
    '''
    
    
    q0 = QuestionYesNo(
    question_name = "second",
    question_text = question_text0_0,
    )
    
    q1 = QuestionYesNo(
    question_name = "info",
    question_text = question_text1_0,
    )

    q2 = QuestionYesNo(
    question_name = "risk",
    question_text = question_text2_0,
    )

    model = Model("gpt-4o")
    survey = Survey(questions = [q0, q1, q2])
    result_all = survey.by(model).run(cache = c)
    
    
    return result_all


def Intervenetion_2P(prompt_s, reasoning, bid, c):
    
    prompt_u = ''
    question_text0_1 = f'''
    {prompt_s}, {prompt_u}
    You chose to bid {bid}. Your reason for that is {reasoning}.
    Give it a second thought. 
    '''
    question_text1_1 = f'''
    {prompt_s}, {prompt_u}
    You chose to bid {bid}. Your reason for that is {reasoning}.
    Now there is additional advice: Let's think step by step. Start with thinking your bidding strategy by 'If I bid down by .., I could... If I bid up by ..., I could...'     
    Give it a second thought.     
    '''

    question_text2_1 = f'''
    {prompt_s}, {prompt_u}
    You chose to bid {bid}. Your reason for that is {reasoning}.
    Now there is additional advice: Do NOT be afraid of risk. All you care about is maximizing expected profit. For example, a 50/50 coin flip between $0 and $105 is more valuable than a payment of $50 to you.     
    Give it a second thought. 
    '''
    
    q0 = QuestionNumerical(
    question_name = "second",
    question_text = question_text0_1,
    )
    
    q1 = QuestionNumerical(
    question_name = "counter",
    question_text = question_text1_1,
    )
    
    q2 = QuestionNumerical(
    question_name = "risk",
    question_text = question_text2_1,
    )

    model = Model("gpt-4o")
    survey = Survey(questions = [q0, q1, q2])
    result_all = survey.by(model).run(cache = c)
    
    return result_all

    

# Define a function to process each plan
def process_plan_ACB(player, reasoning, current_price, value, remaining_bidders, c):
    # sem = survey_plan(reasoning)
    sem = Intervenetion_ACB(player, reasoning, current_price, value, remaining_bidders, c)
    # answer = sem.select("risk", "dynamic", "depend", "learn").to_pandas(remove_prefix=True)
    answer = sem.select("second","risk", "info").to_pandas(remove_prefix=True)
    return answer

def process_plan_2P(prompt_s, reasoning, bid, c):
    # sem = survey_plan(reasoning)
    sem = Intervenetion_2P(prompt_s, reasoning, bid, c)
    # answer = sem.select("risk", "dynamic", "depend", "learn").to_pandas(remove_prefix=True)
    answer = sem.select("second","counter", "risk").to_pandas(remove_prefix=True)
    return answer


def main():
    c = Cache()
    # Load data
    # df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/OSP/drop_output_AC_B.csv")
    
    df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/OSP/prompt_SP.csv")
    # Use ProcessPoolExecutor to process data in parallel
    results = []
        
    with ProcessPoolExecutor() as executor:
        # Submit all jobs to the executor
        futures = [executor.submit(process_plan_2P, row['system_prompt'], row['comment'], row['answer'], c) 
                   for _, row in df.iterrows()]
        
        for future in futures:
            result = future.result()  # Collect results as they complete
            print(result)
            results.append(result)
            
    c.write_jsonl("2P_intervention.jsonl")

    # Concatenate all results into a single DataFrame
    all_results = pd.concat(results, ignore_index=True)

    # Combine the original DataFrame with the new results
    final_df = pd.concat([df, all_results], axis=1)

    # Save the combined DataFrame to a CSV file
    final_df.to_csv("2P_intervention.csv", index=False)

if __name__ == '__main__':
    main()

