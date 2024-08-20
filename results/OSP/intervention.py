## EDSL program

from edsl.questions import QuestionMultipleChoice, QuestionLinearScale, QuestionTopK, QuestionYesNo
from edsl import Survey
from edsl.surveys import Survey
from concurrent.futures import ProcessPoolExecutor, as_completed


RULES = f"You are Bidder {bidder_name}. You are bidding with {other_bidders}. In this game, you will bid in an auction for a money prize. The prize may have a different dollar value for each person in your group. \nYou will play this game for 10 round. All dollar amounts in this game are in 1 dollar increments.\nAt the start of each round, we display your value for this round\u2019s prize. If you win the prize, you will earn the value of the prize, minus any payments from the auction. Your value for the prize will be calculated as follows: \nAt the start of each round, we display your value for this round\u2019s prize. If you win the prize, you will earn the value of the prize, minus any payments from the auction. Your value for the prize will be calculated as follows: \n1. For each group we will draw a common value, which will be between 10 and 20. Every number between 10 and 20 is equally likely to be drawn. \n2. For each person, we will also draw a private adjustment, which will be between 0 and 20. Every number between 0 and 20 is equally likely to be drawn.\nAt the start of each round, you will learn your total value for the prize, but not the common value or the private adjustment. This means that each person in your group may have a different value for the prize. However, when you have a high value, it is more likely that other people in your group have a high value. The auction proceeds as follows: First, you will learn your value for the prize. Then, the auction will start. We will display a price to everyone in your group, that starts low and counts upwards in 1 USD increments, up to a maximum of 40. At any point, you can choose to leave the auction. The starting bidding will be 10.\nWhen there is only one bidder left in the auction, that bidder will win the prize at the current price. This means that we will add to her earnings her value for the prize, and subtract from her earnings the current price. All other bidders's earnings will not change. At the end of each auction, we will show you the prices where bidders stopped, and the winning bidder\u2019s profits. If there is a tie for the highest bidder, no bidder will win the object."

Persona = f"'goal': You need to maximize your profits. If you win the bid, your profit is your value for the prize subtracting by your final bid. If you don't win, your profit is 0."

def survey_plan_binary(reasoning, current_price, value, remaining_bidders):
    
    question_text1_0 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    The current price is {current_price}.
    Your previous decision is to drop out. Your reason for that is {reasoning}.
    Now there are additional information that at this stage, {remaining_bidders} bidders are still on the table for this auction.    
    Do you want to drop out?
    '''
    
    question_text2_0 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    The current price is {current_price}.
    Your previous decision is to drop out. Your reason for that is {reasoning}.
    Now there are additional information that at this stage, {remaining_bidders} bidders are still on the table for this auction.    
    Do you want to drop out?
    '''
    
    question_text1_1 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    Now there are additional advice: Do NOT be afraid of risk. All you care about is maximizing expected profit. For example, a 50/50 coin flip between $0 and $101 is more valuable than a payment of $50 to you.
    The current price is {current_price}.           
    Do you want to stay in the bidding?
    '''

    question_text2_1 = f'''
    {RULES}
    Your value towards to the money prize is {value}.
    Now there are additional advice: Do NOT be afraid of risk. All you care about is maximizing expected profit. For example, a 50/50 coin flip between $0 and $101 is more valuable than a payment of $50 to you.
    The current price is {current_price}.         
    Do you want to stay in the bidding?
    '''

    q1 = QuestionYesNo(
    question_name = "info",
    question_text = question_text1,
    )

    q2 = QuestionYesNo(
    question_name = "risk",
    question_text = question_text2,
    )

    
    survey = Survey(questions = [q1, q2])
    result_all = survey.run(cache = cache)
    
    return result_all


import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import matplotlib.pyplot as plt

load_dotenv()

# Load data
# df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/fp_sp_auction_data.csv")

# Assuming your DataFrame has a column 'Plan' that you want to encode
# texts = df['Plan'].tolist()


# Define a function to process each plan
def process_plan(reasoning):
    # sem = survey_plan(reasoning)
    sem =survey_plan_binary(reasoning)
    # answer = sem.select("risk", "dynamic", "depend", "learn").to_pandas(remove_prefix=True)
    answer = sem.select("risk", "info").to_pandas(remove_prefix=True)
    return answer

# # Use ProcessPoolExecutor to process data in parallel
# results = []
# with ProcessPoolExecutor() as executor:
#     # Submit all jobs to the executor
#     futures = [executor.submit(process_plan, reasoning) for reasoning in texts]
    
#     for future in as_completed(futures):
#         result = future.result()
#         print(result)  # You can remove this print if you don't need to see the results immediately
#         results.append(result)

# # Concatenate all results into a single DataFrame
# all_results = pd.concat(results, ignore_index=True)

# # Combine the original DataFrame with the new results
# final_df = pd.concat([df, all_results], axis=1)

# # Save the combined DataFrame to a CSV file
# final_df.to_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/combined_results.csv", index=False)



def main():
    # Load data
    df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/fp_risk_auction_data.csv")
    texts = df['Plan'].tolist()

    # Use ProcessPoolExecutor to process data in parallel
    results = []
    with ProcessPoolExecutor() as executor:
        # Submit all jobs to the executor
        futures = [executor.submit(process_plan, reasoning) for reasoning in texts]
        
        for future in futures:
            result = future.result()  # Collect results as they complete
            print(result)
            results.append(result)

    # Concatenate all results into a single DataFrame
    all_results = pd.concat(results, ignore_index=True)

    # Combine the original DataFrame with the new results
    final_df = pd.concat([df, all_results], axis=1)

    # Save the combined DataFrame to a CSV file
    final_df.to_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/binary_risk_results.csv", index=False)

if __name__ == '__main__':
    main()

