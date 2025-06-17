## EDSL program

from edsl.questions import QuestionMultipleChoice, QuestionLinearScale, QuestionTopK
from edsl import Survey
from edsl.surveys import Survey
from concurrent.futures import ProcessPoolExecutor, as_completed


def survey_plan_binary(reasoning, value, bid):
    
    question_text1 = f'''Context:

Read the following bidding strategy:

{reasoning}

The bidder with this strategy ends up having a value of {value} and bids {bid}.

Question 1: Assessing Bidding Aggressiveness
Based on the strategy, as well as the actual bid relative to the value, classify the player as "Conservative" or "Aggressive" in their bidding approach. Provide concise reasons for your classification, citing specific elements from the strategy and how the bid compares to the value.

Definitions:

Conservative Bidder: Avoids both significant overbidding (bidding above their own value) to prevent overpaying and significant underbidding (bidding much below their value) to avoid losing the item. Bids close to their true value to minimize risks associated with overpaying or missing out.

Aggressive Bidder: Willingly takes significant risks by overbidding (bidding above their value) to secure the item at all costs or significant underbidding (bidding well below their value) aiming for a low price but risking loss from not getting the item. Employs extreme bidding tactics, accepting higher risks.'''

    question_text2 = f'''Context:

Read the following bidding strategy:

{reasoning}

The bidder with this strategy ends up having a value of {value} and bids {bid}.

Question 2: Strategic Approach
Based on the strategy, assess whether the player employs an "Interactive Strategy" or an "Isolated Strategy." Provide concise reasons for your assessment, citing specific elements from the strategy.

Definitions:

Interactive Strategy: The player considers other bidders' actions to adjust their own bidding strategy. They heavily factor in competitors' behaviors, expectations, or market dynamics as part of their decision-making process.

Isolated Strategy: The player focuses mostly on their own valuation and personal strategy without considering competitors' actions. They base their bidding decisions primarily on individual assessment, independent of others' behaviors.'''

    question_text3 = f'''Context:

Read the following bidding strategy:

{reasoning}

The bidder with this strategy ends up having a value of {value} and bids {bid}.

Question 3: Understanding of Auction Rules
Based on the strategy, the bid, and the value, assess whether the player has a "Weak Understanding" or "Strong Understanding" of the auction rules. Provide concise reasons for your assessment, citing specific elements from the strategy and how the bid relates to the value. 

Definitions:

Weak Understanding: The player lacks fundamental knowledge of second-price auction mechanics, leading to significant strategic errors. Indicators include: Underbidding with Misconception: Bidding below their true value, wrongly believing it will lower the price they pay, not recognizing that the final price is determined by the second-highest bid. Overbidding without Justification: Bidding above their true value without valid strategic reasons, risking overpayment unnecessarily. Misunderstanding Bid Impact: Believing their bid directly sets the price they pay, resulting in ineffective strategies due to this misconception.

Strong Understanding: The player has a clear grasp of second-price auction rules, employing strategies that reflect this knowledge. Indicators include: Bidding True Value: Recognizing that bidding their true value is the optimal strategy to maximize expected utility. Valid Strategic Deviations: If deviating from their true value, doing so with sound reasoning aligned with auction theory (e.g., accounting for risk aversion or anticipating irrational bids from others). Correct Bid Impact Awareness: Understanding that their bid determines if they win, but the price paid is set by the second-highest bid, not their own.'''

    q1 = QuestionLinearScale(
    question_name = "risk2",
    question_text = question_text1,
    question_options = [0,1],
    option_labels = {0:"Conservative Bidder", 1:"Aggressive Bidder"}
    )

    q2 = QuestionLinearScale(
    question_name = "strategy2",
    question_text = question_text2,
    question_options = [0,1],
    option_labels = {0:"Interactive Strategy",1: "Isolated Strategy"}
    )

    q3 = QuestionLinearScale(
    question_name = "understand2",
    question_text = question_text3,
    question_options = [0,1],
    option_labels = { 0:"Weak Understanding", 1:"Strong Understanding",}
    )
    
    survey = Survey(questions = [q1, q2, q3])
    result_all = survey.run()
    
    return result_all
    
    
    # q1 = QuestionLinearScale(
    # question_name = "risk2",
    # question_text = question_text1,
    # question_options = [0,1],
    # option_labels = {0:"Risk-Averse", 1:"Not Risk-Averse"}
    # )

    # question_text2 = f'''
    # "Read the following bidding strategy: {reasoning}. 
    # Do you identify it risk-averse / conservative or NOT risk-averse / aggressive and how much so? Provide detailed reasons for the classification. 
    # Classify along:
    # 1: Completely risk-averse bids correspond to level 1.
    # Balanced, risk-neutral bids correspond to levels 5 - 6.
    # 10: Completely risk-loving, aggressive bids correspond to level 10.

    # There will be bids and values of all different levels. Classify bids in a way thats internally consistent.
    # '''
    # q2 = QuestionLinearScale(
    # question_name = "risk10",
    # question_text = question_text2,
    # question_options = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    # option_labels = {1:"Risk-Averse", 10:"Risk-loving"})

    # survey = Survey(questions = [q1, q2, q3, q4])
    # result_all = survey.run()
    
    # return result_all

def survey_plan(reasoning, value, bid):

    question_text1 = f'''
    "Read the following bidding strategy: {reasoning}. The bidder with this strategy ends up having a value of {value} and bidding {bid}.
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
def process_plan(reasoning, value, bid):
    # sem = survey_plan(reasoning)
    sem =survey_plan_binary(reasoning, value, bid)
    # answer = sem.select("risk", "dynamic", "depend", "learn").to_pandas(remove_prefix=True)
    answer = sem.select("risk2", "strategy2", "understand2").to_pandas(remove_prefix=True)
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
    df = pd.read_csv("/content/sp_risk2_auction_data.csv")
    texts = df['Plan'].tolist()
    values = df['Value'].tolist()
    bids = df['Bid'].tolist()

    # Use ProcessPoolExecutor to process data in parallel
    results = []
    with ProcessPoolExecutor() as executor:
        # Submit all jobs to the executor
        futures = [executor.submit(process_plan, texts[i], values[i], bids[i]) for i in range(len(texts))]
        
        for future in futures:
            result = future.result()  # Collect results as they complete
            print(result)
            results.append(result)

    # Concatenate all results into a single DataFrame
    all_results = pd.concat(results, ignore_index=True)

    # Combine the original DataFrame with the new results
    final_df = pd.concat([df, all_results], axis=1)

    # Save the combined DataFrame to a CSV file
    final_df.to_csv("/content/llm-auction/results/Plan_reflection/sp_binary_risk2_results_new2.csv", index=False)

if __name__ == '__main__':
    main()

