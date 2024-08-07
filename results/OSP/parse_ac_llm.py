## EDSL program

from edsl.questions import QuestionMultipleChoice, QuestionNumerical, QuestionFreeText
from edsl import Survey
from edsl.surveys import Survey
from concurrent.futures import ProcessPoolExecutor, as_completed
from edsl import Model

def survey_plan(reasoning):

    question_text1 = f'''
    Read the following bidding history: {history}. Find the sentence "Your value towards to the money prize is ..."
    What's the value for this bidder?
    '''

    question_text2 = f'''
    Read the following bidding history: {history}. Find the sentence "The current price is ..."
    What's the current price in the clock auction?
    '''

    question_text3 = f'''
    Read the following bidding history: {history}. Find the sentence "You are bidder ..."
    What's the number of the bidder?
    '''

    question_text4 = f'''
    Read the following bidding history: {history}. Find the sentence "\\\"answer\\\": "
    What's the answer from the bidder? Is it 0 or 1?
    '''
    
    question_text4 = f'''
    Read the following bidding history: {history}. Find the sentence "\\\"comment\\\": "
    What's the comment from the bidder? Directly copy and copy the sentence after the comment.
    '''

    q1 = QuestionNumerical(
    question_name = "name",
    question_text = question_text1,
    question_options = [0,1,2,3,4],
    option_labels = {0:"Conservative", 4:"Aggressive"}
    )

    q2 = QuestionNumerical(
    question_name = "dynamic",
    question_text = question_text2,
    question_options = [0,1,2,3,4],
    option_labels = {0:"Static",4: "Dynamic"}
    )

    q3 = QuestionFreeText(
    question_name = "depend",
    question_text = question_text3,
    question_options = [0,1,2,3,4],
    option_labels = { 0:"Independent", 4:"Reactive",}
    )

    q4 = QuestionNumerical(
    question_name = "learn",
    question_text = question_text4,
    question_options = [0,1,2,3,4],
    option_labels = {0: "Non-Reflective", 4: "Reflective"}
    )
    
    model = Model('gpt-4o-mini', temperature =0)
    
    survey = Survey(questions = [q1, q2, q3, q4]).by(model)
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

