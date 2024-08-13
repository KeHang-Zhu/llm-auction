## EDSL program

from edsl.questions import QuestionMultipleChoice, QuestionLinearScale, QuestionTopK
from edsl import Survey
from edsl.surveys import Survey
from concurrent.futures import ProcessPoolExecutor, as_completed


def survey_plan_RA(reasoning, levels = 'NO'):

    if levels == 'NO':
        question_text1 = f'''
        "Read the following bidding strategy: {reasoning}. 
        Do you identify it risk-averse / conservative or NOT risk-averse / aggressive? Provide detailed reasons for the classification. 
        Classify along:
        Risk-averse: Prefers minimal risk.
        Not risk-averse: Willing to take high risks with the potential for high returns.        
        '''
        q1 = QuestionLinearScale(
        question_name = "risk",
        question_text = question_text1,
        question_options = [0,1],
        option_labels = {0:"Risk-Averse", 4:"Not Risk-Averse"}
        )
    else:
        question_text1 = f'''
        "Read the following bidding strategy: {reasoning}. 
        Do you identify it risk-averse / conservative or NOT risk-averse / aggressive and how much so? Provide detailed reasons for the classification. 
        Classify along:
        1: Completely risk-averse bids correspond to level 1.
        Balanced, risk-neutral bids correspond to levels 5 - 6.
        10: Completely risk-loving, aggressive bids correspond to level 10.

        There will be bids and values of all different levels. Classify bids in a way thats internally consistent.
        '''
        q1 = QuestionLinearScale(
        question_name = "risk",
        question_text = question_text1,
        question_options = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        # option_labels = {0:"Risk-Averse", 4:"Not Risk-Averse"}

    survey = Survey(questions = [q1])
    result_all = survey.run()
    
    return result_all

def survey_plan(reasoning):

    question_text1 = f'''
    "Read the following bidding strategy: {reasoning}. 
    Do you identify it as aggressive, conservative, or balanced? Provide detailed reasons for the classification. 
    The operational Levels are:
    Aggressive 4: Willing to take high risks with the potential for high returns; often bids significantly above value to outcompete others.
    Normal 3: Bidding their true value, i.e. 100% of the value.
    Conservative 0: Prefers minimal risk, usually bids far below their value to avoid losses.

    Example 1: 
    Input: "I will explore implementing a conditional strategy, varying my bidding based on the opponents' prior habits. A pivot to higher bids for values above 50, around 80-90%, while maintaining a conservative 30-40% for lower values. Learning and capitalizing on competitors' behaviors will be a priority. " 
    Output: medium, 2
    
    Example 2: 
    Input: “For values under $30, I'll adopt a conservative approach, bidding around 30% of the value. Over $30, I'll bid 70-90% of the value. I'll use random bids occasionally to confuse competitors, while keenly watching their strategies for adjustments. Lastly, in a prospective tie, I'll increase my bid slightly for a guaranteed win.”
    Output: Little Conservative, 1
    '''

    question_text2 = f'''
    Read the following bidding strategy: {reasoning}. 
    Do you identify it as static, dymanic? Provide detailed reasons for the classification. 
    The Operational Levels are:
    Static 0: Sticks to a predefined strategy regardless of changes during the auction.
    Dynamic 4: Regularly adjusts strategies in response to auction flow and other bidders’ actions.
    '''

    question_text3 = f'''
    Read the following bidding strategy: {reasoning}. 
    Do you identify it as reactive or independent? Provide detailed reasons for the classification. 
    The Operational Levels are:
    Reactive 4: Modifications to the strategy are heavily based on opponents' actions.
    Independent 0: Strategy is mostly unaffected by opponents' actions.
    
    Example 1: 
    Input: Next, for values >90, bid 80-90. For 70-90, bid 60-75. For <70, bid actual value or slightly higher. Also, explore occasional random and aggressive bids on lower values, adjusting strategy based on opponent's patterns. Balance risks, profit maximization is key.
    Output: 0 Independent
    
    Example 2:
    Input: plan to incrementally raise my bids in next rounds to study opponents' tendencies. I will bid higher when my value is high, and moderate for low values, observing profits against aggressive and conservative strategies
    Output: 3 little reactive
    '''

    question_text4 = f'''
    Read the following bidding strategy: {reasoning}. 
    To which degree do you identify it as reflective? Provide detailed reasons for the classification. 
    The Operational Levels from 4 to 0 are:
    Reflective 4: Actively learns from each bid, adapting strategies based on past outcomes.
    Occasionally Reflective 1: Learns from particularly significant outcomes but does not consistently reflect.
    Non-Reflective 0: Rarely if ever adjusts strategy based on past bids.
    '''

    q1 = QuestionLinearScale(
    question_name = "risk",
    question_text = question_text1,
    question_options = [0,1,2,3,4],
    option_labels = {0:"Conservative", 4:"Aggressive"}
    )

    q2 = QuestionLinearScale(
    question_name = "dynamic",
    question_text = question_text2,
    question_options = [0,1,2,3,4],
    option_labels = {0:"Static",4: "Dynamic"}
    )

    q3 = QuestionLinearScale(
    question_name = "depend",
    question_text = question_text3,
    question_options = [0,1,2,3,4],
    option_labels = { 0:"Independent", 4:"Reactive",}
    )

    q4 = QuestionLinearScale(
    question_name = "learn",
    question_text = question_text4,
    question_options = [0,1,2,3,4],
    option_labels = {0: "Non-Reflective", 4: "Reflective"}
    )
    
    survey = Survey(questions = [q1, q2, q3, q4])
    result_all = survey.run()
    
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
    sem = survey_plan(reasoning)
    answer = sem.select("risk", "dynamic", "depend", "learn").to_pandas(remove_prefix=True)
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
    df = pd.read_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/fp_sp_auction_data.csv")
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
    final_df.to_csv("/Users/wonderland/Desktop/auction/llm-auction/results/Plan_reflection/scaled_results.csv", index=False)

if __name__ == '__main__':
    main()

