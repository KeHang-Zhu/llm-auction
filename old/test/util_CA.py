import textwrap
from textwrap import dedent
from itertools import cycle
import random
import json
import os
import sys
from edsl import shared_globals
from edsl import Model
from edsl import Agent, Scenario, Survey
from edsl.data import Cache
from edsl.Base import Base
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionNumerical
from jinja2 import Template


current_script_path = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_script_path, './rule_template/V7/')

# c = Cache()  

def save_json(data, filename, directory):
    """Save data to a JSON file in the specified directory."""
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    return file_path

class Rule_CA:
    '''
    This class defines different auction rules and their behaviors.
    '''
    def __init__(self, seal_clock,  private_value, open_blind, rounds, 
                 ascend_descend="ascend",
                 price_order = "second",
                 CA_type = "simultaneous",
                 common_range=[10, 80], private_range=20, increment=1, number_agents=3):
        self.seal_clock = seal_clock
        self.ascend_descend = ascend_descend
        self.private_value = private_value
        self.open_blind = open_blind
        self.price_order = price_order
        self.round = rounds
        self.common_range = common_range
        self.private_range = private_range
        self.increment = increment
        self.number_agents = number_agents
        self.type = CA_type
        
        ## Rule prompt
        # intro_string = Prompt.from_txt(os.path.join(templates_dir,"intro.txt"))
        # intro = intro_string.render({"n":self.round})

        # value_explain_string = Prompt.from_txt(os.path.join(templates_dir,f"intro_{self.private_value}.txt"))
        # value_explain = value_explain_string.render({"increment":self.increment,"common_low":self.common_range[0], "common_high":self.common_range[1],"private":self.private_range, "num_bidders": self.number_agents-1})
        

        game_type_string = Prompt.from_txt(os.path.join(templates_dir,f"{self.type}_FP.txt"))
        game_type = game_type_string.render({"increment":self.increment,"min_price":self.common_range[0],"max_price":self.common_range[1]+self.private_range, "common_low":self.common_range[0], "common_high":self.common_range[1],"num_bidders": self.number_agents-1, "private":self.private_range, "n":self.round})
        
        # if self.round > 1:
        #     multi_string = Prompt.from_txt(os.path.join(templates_dir,"multi.txt"))
        #     ending = multi_string.render({"n":self.round})
        # else:
        #     ending = ''
        
        ## Combine the rule prompt
        self.rule_explanation =  game_type
        
        self.persona = "Your TOP PRIORITY is to place bids which maximize your profit in the long run. To do this, you should explore many different bidding strategies, including possibly risky or aggressive options for data-gathering purposes. Learn from the history of previous rounds in order to maximize your total profit. Don't forget the values are redrawn independently each round."
        
        ## Bid asking prompt
        if self.type == "sequential":
            self.asking_prompt1 = "Now you are at the first stage bidding for A. How much would you like to bid on A?  Give your response with a single number and no other texts, e.g. 1, 44. Start with For A, I bid... "
            self.asking_prompt2 = "Now you are at the second stage bidding for B. How much would you like to bid on B?  Give your response with a single number and no other texts, e.g. 1, 44. Start with For B, I bid... "
        elif self.type == "simultaneous":
            self.asking_prompt = """How much would you like to bid on each item?  Give your response with a single number and no other texts, e.g. 1, 44. Start with For A, I bid... For B, I bid...  """
        elif self.type == "menu":
            self.asking_prompt = """How much would you like to bid on each menu?  Give your response with a single number and no other texts, e.g. 1, 44. Start with For A, I bid... For B, I bid... For AB, I bid... """
                

    def describe(self):
        # Provides a description of the auction rule
        print(f"Auction Type: {self.seal_clock}, \nBidding Order: {self.ascend_descend}, \nValue Type: {self.private_value}, \n Information Type: {self.open_blind}, \n price order: {self.price_order}")


class SealBid():
    def __init__(self, agents, rule, model, cache= None, history=None):
        
        ## for setting up stage
        self.rule = rule
        self.agents = agents
        ## For repeated game:
        self.history = history
        self.model = model
        self.cache = cache
        
        # self.scenario = Scenario({
        #     'agent_1_name': agents[0].name, 
        #     'agent_2_name': agents[1].name, 
        #     'the history of this game': self.history
        #     }) 
        
        ## for bidding 
        self.bid_list = []
        self.winner = None
        
        
    def __repr__(self):
        return f'Sealed Bid Auction: (bid_list={self.bid_list})'
    
    def run_off_box(self):
        '''run for one round with out-of-box LLM query'''

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction = f"""
            You are {agent.name}. 
            You are bidding with { other_agent_names}.
            Your value towards to the prize is {agent.current_value} in this round.
            """
            q_bid = QuestionNumerical(
                question_name = "q_bid",
                question_text = instruction + self.rule.asking_prompt
            )

            survey = Survey(questions = [q_bid])
            result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
            response = result.select("q_bid").to_list()[0]
            agent.reasoning.append(result.select("comment.*")[0]['comment.q_bid_comment'][0])
            self.bid_list.append({"agent":agent.name,"bid": response})
            agent.submitted_bids.append(response)
            
        print(self.bid_list)
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}
    
    def parse_bid(self, bid, mode="A"):
        # while (bid is None or valid_bid is False) and retry_count < max_retries:
        parse_model =  Model('gpt-4o', temperature=0)
            
        if self.rule.type == "sequential":
            if mode == "A":
                q_parse_A = QuestionNumerical(
                    question_name = "q_parse_A",
                    question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on item A, only return a number, for example, 0 or 44 "
                )
                result_A =  parse_model.simple_ask(q_parse_A)
                parsed_bid = {"A": float(result_A['choices'][0]['message']['content'])}
            elif mode =="B":
                q_parse_B = QuestionNumerical(
                question_name = "q_parse_B",
                question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on item B, only return a number, for example, 0 or 44"
                )
                result_B =  parse_model.simple_ask(q_parse_B)
                parsed_bid = {"B": float(result_B['choices'][0]['message']['content'])}
        
        elif self.rule.type == "simultaneous":
            q_parse_A = QuestionNumerical(
                    question_name = "q_parse_A",
                    question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on item A, only return a number, for example, 0 or 44 "
                )
            result_A =  parse_model.simple_ask(q_parse_A)
            parsed_bid = {"A": float(result_A['choices'][0]['message']['content'])}
            q_parse_B = QuestionNumerical(
                question_name = "q_parse_B",
                question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on item B, only return a number, for example, 0 or 44"
            )
            result_B =  parse_model.simple_ask(q_parse_B)
            
            parsed_bid = {"A": float(result_A['choices'][0]['message']['content']), "B": float(result_B['choices'][0]['message']['content'])}
        elif self.rule.type == "menu":
            q_parse_B = QuestionNumerical(
                question_name = "q_parse_B",
                question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on item B, only return a number, for example, 0 or 44"
            )
            result_B =  parse_model.simple_ask(q_parse_B)
            q_parse_AB = QuestionNumerical(
                question_name = "q_parse_AB",
                question_text = "You are a helpful assistant, you receive a bidding message from a participant." + str(bid) + "Return the bid amount on bundle of AB, only return a number, for example, 0 or 44"
            )
            result_AB =  self.model.simple_ask(q_parse_AB)
            parsed_bid = {"A": float(result_A['choices'][0]['message']['content']), "B": float(result_B['choices'][0]['message']['content']), "AB": float(result_AB['choices'][0]['message']['content'])}  
        
        print(parsed_bid)
        return parsed_bid
        
    def seq_bid(self):
        '''Bidding for the sequential CA'''
        ## Bidding for A
        
        if len(self.agents[0].reasoning) == 0:
            bid_list = []
            for agent in self.agents:
                other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
                combined_value = 2 *(agent.current_value["A"]+ agent.current_value["B"])
                instruction = f"""
                You are {agent.name}. 
                You are bidding with { other_agent_names}.
                Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}.
                """
            
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" +  "write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. Your plan should be within 100 words"
                    )
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan_A = result.select("q_plan").to_list()[0]
                print(plan_A)
                
                q_bid_A = QuestionFreeText(
                        question_name = "q_bid_A",
                        question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona +  "This is the first round " + "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """ + "Your PLAN for this round is:" + str(plan_A)  + "FOLLOW YOUR PLAN " + self.rule.asking_prompt1
                            )
                survey = Survey(questions=[q_bid_A])
                result_A = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid_A = result_A.select("q_bid_A").to_list()[0]
                print(bid_A)
                parsed_bid = self.parse_bid(bid_A, mode="A")
                agent.reasoning.append({"A":plan_A})
                bid_list.append({"agent":agent.name,"bid": parsed_bid})
                
            #determine the winner
            bidding_A = self.determine_winner_sequ(bid_list)
            print(bidding_A)
        
            ## Bidding for B
            for agent in self.agents:
                ## generate sentence of the results for A
                if bidding_A["winner"] is agent.name:
                    status_A = "You won the item A. "
                else:
                    status_A = "You didn't win the item A. "
                plan = agent.reasoning[-1]["A"]
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" +  "Your PLAN at the start of this round is:" + str(plan)+ "And in the previous bidding of A: " + str(status_A)+ "update your plans for what bidding strategies for B. Be detailed and precise but keep things succinct and don't repeat yourself. Your plan should be within 100 words"
                    )
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan_B = result.select("q_plan").to_list()[0]
                print(plan_B)
                
                q_bid_B = QuestionFreeText(
                        question_name = "q_bid_B",
                        question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona +  "This is the first round " + "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """+  "And in the previous bidding of A: " + str(status_A)+ " Your PLAN of bidding B for this round is:" + str(plan_B)  + " FOLLOW YOUR PLAN "  + self.rule.asking_prompt2
                            )
                survey = Survey(questions=[q_bid_B])
                result_B =  survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid_B = result_B.select("q_bid_B").to_list()[0]
                print(bid_B)
                parsed_bid = self.parse_bid(bid_B, mode="B")
                agent.reasoning[-1]["B"] = plan_B
                bid_list.append({"agent":agent.name,"bid": parsed_bid})
                
        else:
            bid_list = []
            for agent in self.agents:
                last_round = agent.history[-1]
                other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
                combined_value = 2 *(agent.current_value["A"]+ agent.current_value["B"])
                instruction = f"""
                You are {agent.name}. 
                You are bidding with { other_agent_names}.
                Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}.
                """
                q_counterfact = QuestionFreeText(
                    question_name = "q_counterfact",
                    question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round history is: " + last_round + "\n" +" Do a counterfactual analysis of the last round. REMEMBER that your goal is to win the bid and make higher profits. REMEMBER YOUR PAYMENT IS YOUR BID IF YOU WIN. Let's think step by step. Start your reflection with 'If I bid down by .., I could... If I bid up by ..., I could...' LIMIT your OUTPUT within 100 words. "
                )
                result = self.model.simple_ask(q_counterfact)
                counterfact= result['choices'][0]['message']['content']
                print("=========================== \n", counterfact)
                
                history = agent.history
                reasoning = agent.reasoning
                max_length = max(len(history), len(reasoning))
                history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i]["A"]+reasoning[i]["B"] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i]["A"]+reasoning[i]["B"] for i in range(max_length)])
                # previous_plan = agent.reasoning[-1]
                q_plan = QuestionFreeText(
                question_name = "q_plan",
                question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round histories along with your plans are: " + history_prompt + f"After careful reflection on previous bidding, your analysis for last round is {counterfact} "+" learn from your previous rounds, Let's think step by step to make sure we make a good choice. Write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. LIMIT your plan to 100 words. "
                )
            
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan_A = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan_A, "====================\n")
                
                q_bid_A = QuestionFreeText(
                        question_name = "q_bid_A",
                        question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona +  "This is the first round " + "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """ + "Your PLAN for this round is:" + str(plan_A)  + "FOLLOW YOUR PLAN " + self.rule.asking_prompt1
                            )
                survey = Survey(questions=[q_bid_A])
                result_A =  survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid_A = result_A.select("q_bid_A").to_list()[0]
                print(bid_A)
                parsed_bid = self.parse_bid(bid_A, mode="A")
                agent.reasoning.append({"A":plan_A})
                bid_list.append({"agent":agent.name,"bid": parsed_bid})
                
            #determine winner
            bidding_A = self.determine_winner_sequ(bid_list)
        
            ## Bidding for B
            for agent in self.agents:
                ## generate sentence of the results for A
                if bidding_A["winner"] is agent.name:
                    status_A = "You won the item A. "
                else:
                    status_A = "You didn't win the item A. "
                plan_A = agent.reasoning[-1]["A"]
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" +  "Your PLAN at the start of this round is:" + str(plan_A)+ "And in the previous bidding of A: " + str(status_A)+ "update your plans for what bidding strategies for B. Be detailed and precise but keep things succinct and don't repeat yourself. Your plan should be within 100 words"
                    )
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan_B = result.select("q_plan").to_list()[0]
                print(plan_B)
                q_bid_B = QuestionFreeText(
                        question_name = "q_bid_B",
                        question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona +  "This is the first round " + "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """ + "And in the previous bidding of A: " + str(status_A)+ " Your PLAN of bidding B for this round is:" + str(plan_B)  + " FOLLOW YOUR PLAN "  + self.rule.asking_prompt2
                            )
                survey = Survey(questions=[q_bid_B])
                result_B =  survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid_B = result_B.select("q_bid_B").to_list()[0]
                print(bid_B)
                parsed_bid = self.parse_bid(bid_B, mode="B")
                agent.reasoning[-1]["B"] = plan_B
                bid_list.append({"agent":agent.name,"bid": parsed_bid})
                
        ## update bid list by adding bid of B
        combined_bids = {}

        # Iterate through the original list of bids
        for item in bid_list:
            agent_name = item["agent"]
            bid = item["bid"]
            # Check if the agent is already in the combined_bids dictionary
            if agent_name in combined_bids:
                # If there's already an entry for this agent, update the bid dictionary
                combined_bids[agent_name]["bid"].update(bid)
            else:
                # If there's no entry for this agent, add one to the dictionary
                combined_bids[agent_name] = {"agent": agent_name, "bid": bid}
                
        self.bid_list=list(combined_bids.values())
        for agent in self.agents:
            agent.submitted_bids.append(combined_bids[agent.name]["bid"])
            
        print(self.bid_list)
        self.determine_payment()
        print(self.winner)

        return {'bidding history':self.bid_list, 'winner':self.winner}
            
    def sim_bid(self):
        
        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            combined_value = 2 *(agent.current_value["A"]+ agent.current_value["B"])
            instruction = f"""
            You are {agent.name}. 
            You are bidding with { other_agent_names}.
            Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}.
            """
            if len(agent.reasoning) == 0:
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" +  "write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. Your plan should be within 100 words"
                    )
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan = result.select("q_plan").to_list()[0]
                print(plan)
                    
                q_bid = QuestionFreeText(
                    question_name = "q_bid",
                    question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona +  "This is the first round " + "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """ + "Your PLAN for this round is:" + str(plan)  + "FOLLOW YOUR PLAN " + self.rule.asking_prompt
                        )
                survey = Survey(questions=[q_bid])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid = result.select("q_bid").to_list()[0]
                print(bid)
                
            else:
                last_round = agent.history[-1]
                q_counterfact = QuestionFreeText(
                    question_name = "q_counterfact",
                    question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round history is: " + last_round + "\n" +" Do a counterfactual analysis of the last round. REMEMBER that your goal is to win the bid and make higher profits. REMEMBER YOUR PAYMENT IS YOUR BID IF YOU WIN. Let's think step by step. Start your reflection with 'If I bid down by .., I could... If I bid up by ..., I could...' LIMIT your OUTPUT within 100 words. "
                )
                result = self.model.simple_ask(q_counterfact)
                counterfact= result['choices'][0]['message']['content']
                print("=========================== \n", counterfact)
                
                history = agent.history
                reasoning = agent.reasoning
                max_length = max(len(history), len(reasoning))
                history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i] for i in range(max_length)])
                # previous_plan = agent.reasoning[-1]
                q_plan = QuestionFreeText(
                question_name = "q_plan",
                question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round histories along with your plans are: " + history_prompt + f"After careful reflection on previous bidding, your analysis for last round is {counterfact} "+" learn from your previous rounds, Let's think step by step to make sure we make a good choice. Write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. LIMIT your plan to 50 words. "
                )
            
                # print(q_plan)
                # result = self.model.simple_ask(q_plan)
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan, "====================\n")
                
                q_bid = QuestionFreeText(
                question_name = "q_bid",
                question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona + "\n" + f"Your analysis for last round is: {counterfact}" "\n" + f"""Your value towards to the A is {agent.current_value["A"]} and your value towards to the B is {agent.current_value["B"]} in this round. Your value towards A and B combined (AB) is {combined_value}. """ + f"Your PLAN for this round is: {plan}" + "FOLLOW YOUR PLAN" + self.rule.asking_prompt
                )
                
                max_retries = 5
                retry_count = 0
                bid = None

                while bid is None and retry_count < max_retries:
                    survey = Survey(questions=[q_bid])
                    result = survey.by(self.model).run(
                        remote_inference_description="check remote reuse",
                        remote_inference_visibility="public"
                    )
                    bid = result.select("q_bid").to_list()[0]
                    retry_count += 1

                if bid is None:
                    # Handle the case where no bid is received after 5 retries
                    print("Failed to get a bid after 5 attempts.")
                    bid = 0
                else:
                    # Use the bid value
                    print(f"Received bid: {bid}")
                    
                print(bid) 
                
            parsed_bid = self.parse_bid(bid)
            self.bid_list.append({"agent":agent.name,"bid": parsed_bid})
            agent.reasoning.append(plan)
            agent.submitted_bids.append(parsed_bid)
            
        print(self.bid_list)
        self.determine_payment()
        print(self.winner)

        return {'bidding history':self.bid_list, 'winner':self.winner}
            
        
    def determine_payment(self):

        if self.rule.type == "simultaneous" or self.rule.type =="sequential":
            # Initialize dictionaries to store highest bids and respective agents
            highest_bids = {'A': [], 'B': []}
            highest_amounts = {'A': float('-inf'), 'B': float('-inf')}

            # Iterate through the bid list to determine the highest bids
            for bid in self.bid_list:
                agent = bid['agent']
                bid_amounts = bid['bid']
                for item in bid_amounts:
                    if bid_amounts[item] > highest_amounts[item]:
                        highest_amounts[item] = bid_amounts[item]
                        highest_bids[item] = [agent]
                    elif bid_amounts[item] == highest_amounts[item]:
                        highest_bids[item].append(agent)

            # Resolve ties randomly and set winners and prices
            winners = {}
            for item in highest_bids:
                if highest_bids[item]:
                    winners[item] = random.choice(highest_bids[item])
            
            self.winner = {
                "A": {'winner': winners['A'], 'price': highest_amounts['A']},
                "B": {'winner': winners['B'], 'price': highest_amounts['B']}
            }
            print(self.winner)
            for agent in self.agents:
                won_a = agent.name == winners['A']
                won_b = agent.name == winners['B']
                
                if won_a and won_b:
                    # The agent won both items
                    agent.profit.append(2*agent.current_value['A'] + 2*agent.current_value['B'] - highest_amounts['A'] - highest_amounts['B'])
                elif won_a:
                    # The agent won item A only
                    agent.profit.append(agent.current_value['A'] - highest_amounts['A'])
                elif won_b:
                    # The agent won item B only
                    agent.profit.append(agent.current_value['B'] - highest_amounts['B'])
                else:
                    # The agent didn't win anything
                    agent.profit.append(0)

                agent.winning.append({"A": won_a, "B": won_b})
                
        elif self.rule.type == "menu":
            # Menu auction logic
            highest_bids = {'A': [], 'B': [], 'AB': []}
            highest_amounts = {'A': float('-inf'), 'B': float('-inf'), 'AB': float('-inf')}

            for bid in self.bid_list:
                agent = bid['agent']
                bid_amounts = bid['bid']
                for item in bid_amounts:
                    if bid_amounts[item] > highest_amounts[item]:
                        highest_amounts[item] = bid_amounts[item]
                        highest_bids[item] = [agent]
                    elif bid_amounts[item] == highest_amounts[item]:
                        highest_bids[item].append(agent)

            for item in highest_bids:
                if len(highest_bids[item]) > 1:
                    highest_bids[item] = [random.choice(highest_bids[item])]

            allocation = {}
            pricing = {}

            if highest_amounts['AB'] > (highest_amounts['A'] + highest_amounts['B']):
                allocation['A'] = highest_bids['AB'][0]
                allocation['B'] = highest_bids['AB'][0]
                pricing['A'] = highest_amounts['AB']/2
                pricing['B'] = highest_amounts['AB']/2
            else:
                allocation['A'] = highest_bids['A'][0]
                allocation['B'] = highest_bids['B'][0]
                pricing['A'] = highest_amounts['A']
                pricing['B'] = highest_amounts['B']

            self.winner = allocation

            for agent in self.agents:
                won_a = agent.name == allocation['A']
                won_b = agent.name == allocation['B']
                
                if won_a and won_b:
                    agent.profit.append(2*(agent.current_value['A'] + agent.current_value['B']) - pricing['A'] - pricing['B'])
                elif won_a:
                    agent.profit.append(agent.current_value['A'] - pricing['A'])
                elif won_b:
                    agent.profit.append(agent.current_value['B'] - pricing['B'])
                else:
                    agent.profit.append(0)

                agent.winning.append({"A": won_a, "B": won_b})
        else: 
            raise ValueError(f"Rule {self.rule.price_order} not allowed")
        
        
    def determine_winner_sequ(self, bid_list):
        '''Sort the bid list by the 'bid' key in descending order to find the highest bids'''
        sorted_bids = sorted(bid_list, key=lambda x: float(x['bid']["A"]), reverse=True)

        if len(sorted_bids) > 0:
            same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
            winner = random.choice(same_bids)["agent"]
            # winner = sorted_bids[0]["agent"]
            price = sorted_bids[0]["bid"]
        
        winner_A = {'winner':winner, 'price':price}
        
        return winner_A
    
        
    def run_with_plan(self):
        '''run for one round'''

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction = f"""
            You are {agent.name}. 
            You are bidding with { other_agent_names}.
            """
            
            if len(agent.reasoning) == 0:
                q_plan = QuestionFreeText(
                question_name = "q_plan",
                question_text = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" +  "write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. Your plan should be within 100 words"
                )
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan)
                
                q_bid = QuestionNumerical(
                question_name = "q_bid",
                question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona + "This is the first round " + "\n" + f" Your value towards to the prize is {agent.current_value} in this round." + "Your PLAN for this round is:" + str(plan)  + "FOLLOW YOUR PLAN " + self.rule.asking_prompt
                    )
                survey = Survey(questions=[q_bid])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                bid = result.select("q_bid").to_list()[0]
                
            else:
                last_round = agent.history[-1]
                q_counterfact = QuestionFreeText(
                    question_name = "q_counterfact",
                    question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round history is: " + last_round + "\n" +" Do a counterfactual analysis of the last round. REMEMBER that your goal is to win the bid and make higher profits. REMEMBER YOUR PAYMENT IS YOUR BID IF YOU WIN. Let's think step by step. Start your reflection with 'If I bid down by .., I could... If I bid up by ..., I could...' LIMIT your OUTPUT within 100 words. "
                )
                result = self.model.simple_ask(q_counterfact)
                counterfact= result['choices'][0]['message']['content']
                print("=========================== \n", counterfact)
                
                history = agent.history
                reasoning = agent.reasoning
                max_length = max(len(history), len(reasoning))
                history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i] for i in range(max_length)])
                # previous_plan = agent.reasoning[-1]
                q_plan = QuestionFreeText(
                question_name = "q_plan",
                question_text = str(self.rule.rule_explanation) + "\n" + instruction + self.rule.persona + "The previous round histories along with your plans are: " + history_prompt + f"After careful reflection on previous bidding, your analysis for last round is {counterfact} "+" learn from your previous rounds, Let's think step by step to make sure we make a good choice. Write your plans for what bidding strategies to test next. Be detailed and precise but keep things succinct and don't repeat yourself. LIMIT your plan to 50 words. "
                )
            
                # print(q_plan)
                # result = self.model.simple_ask(q_plan)
                survey = Survey(questions = [q_plan])
                result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan, "====================\n")
                
                q_bid = QuestionNumerical(
                question_name = "q_bid",
                question_text =  str(self.rule.rule_explanation) + "\n" +instruction + self.rule.persona + "\n" + f"Your analysis for last round is: {counterfact}" "\n" + f" Your value towards to the prize is {agent.current_value} in this round."+ f"Your PLAN for this round is: {plan}" + "FOLLOW YOUR PLAN" + self.rule.asking_prompt
                    )
                # print(q_bid)
                # result = self.model.simple_ask(q_bid)
                # response = result['choices'][0]['message']['content']
                max_retries = 5
                retry_count = 0
                bid = None

                while bid is None and retry_count < max_retries:
                    survey = Survey(questions=[q_bid])
                    result = survey.by(self.model).run(
                        remote_inference_description="check remote reuse",
                        remote_inference_visibility="public"
                   )
                    bid = result.select("q_bid").to_list()[0]
                    retry_count += 1

                if bid is None:
                    # Handle the case where no bid is received after 5 retries
                    print("Failed to get a bid after 5 attempts.")
                    bid = 0
                else:
                    # Use the bid value
                    print(f"Received bid: {bid}")
            # print(response)

            agent.reasoning.append(plan)
            self.bid_list.append({"agent":agent.name,"bid": bid})
            agent.submitted_bids.append(bid)
            
        print(self.bid_list, '\n Value list:',[agent.current_value for agent in self.agents])
        # self.declare_winner_and_price()
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}
    

    
class Clock():
    def __init__(self, agents, rule, model, cache=None, history=None):
        
        ## for setting up stage
        self.rule = rule
        self.agents = agents[:]
        self.change = self.rule.increment
        self.current_price = rule.common_range[0]
        self.model = model
        self.cache = cache
        ## For repeated game:
        self.history = history
        
        if self.rule.ascend_descend == "ascend":
            self.agent_left = agents[:]
        elif self.rule.ascend_descend == "descend":
            self.agent_left = []
        
        # For bidding storage
        self.clock = 0
        self.exit_number = 0
        self.current_bid = []
        self.bid_list = []    
        self.transcript = []
        self.exit_list = []
        self.winner = None
    
    def __repr__(self):
        return f'Clock Auction: (bid_list={self.bid_list})'
        
    def dynamic(self):
        if self.rule.ascend_descend == "ascend":
            self.current_price +=self.change
        elif self.rule.ascend_descend == "descend":
            self.current_price -=self.change
        else:
            raise ValueError(f"Rule {self.rule.ascend_descend} not allowed")
    
    def run_one_clock(self):
        '''run for one round'''
        self.exit_number = 0
        print("===========",self.current_price)
        agent_in_play = self.agent_left[:]
        
        for agent in agent_in_play:
            other_agent_names = ', '.join([a.name for a in agent_in_play if a is not agent])

            instruction = f"""
            You are {agent.name}.
            You are bidding with { other_agent_names}.
            Your value towards to the prize is {agent.current_value} in this round.
            """
                 
            q_bid = QuestionYesNo(
                question_name = "q_bid",
                question_text = instruction+ f"""
            The previous biddings are: {self.transcript}.\n
            The current price is {self.current_price}. \n
            {self.rule.asking_prompt}""",
            )
            # print(instruction)
            # print(q_bid)
            # print(agent)
            # scenario = Scenario()
            # agent = Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds")
            survey = Survey(questions = [q_bid])
            result = survey.by(self.model).run(
                    remote_inference_description="check remote reuse",
                    remote_inference_visibility="public"
                )
            response = result.select("q_bid").to_list()[0]
            
            print("=========",agent.name, response)

            if self.rule.ascend_descend == 'ascend':
                if response.lower() == 'no':
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
                    self.agent_left.remove(agent)
                    agent.exit_price.append(str(self.current_price))
                    self.exit_number += 1
                    self.exit_list.append({"agent":agent.name,"bid": self.current_price})
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
            elif self.rule.ascend_descend == 'descend':
                if response.lower() == 'yes':
                    self.agent_left.append(agent)
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
                    agent.exit_price.append(str(self.current_price))
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
            
        ## update the shared information
        self.transcript.append(self.share_information())
        
    def run(self):
        '''Run the clock until the ending condition'''
        stop_condition = False
        while stop_condition is False:
            self.bid_list = []
            self.run_one_clock()
            print(self.clock+1, '+++++done')
            self.clock +=1
            stop_condition = self.declear_winner_and_price()
            ## calculate the next clock price
            self.dynamic()
            print(self.__repr__())
            
        print(self.winner)
        for agent in self.agents:
            if agent.name == self.winner["winner"]:
                agent.profit.append(agent.current_value - float(self.winner["price"]))
                agent.exit_price.append(str(self.winner["price"]))
                agent.winning.append(True)
            else:
                agent.profit.append(0)
                agent.winning.append(False)
        return {'bidding history':self.exit_list, 'winner':self.winner}
    
    def share_information(self):
        if self.rule.open_blind == "open":
            if self.exit_number == 0:
                return f'In clock round {self.clock+1}, the price was {self.current_price}, no players dropped out'
            else:
                return f'In clock round {self.clock+1}, the price was {self.current_price}, {self.exit_number} players dropped out'
        elif self.rule.open_blind == "blind":
            return None


    def declear_winner_and_price(self):
        ## The rules for deciding winners
        if self.rule.ascend_descend == "ascend":
            if len(self.agent_left) == 1:
                winner = self.agent_left[0].name
                price = self.current_price
                self.winner = {'winner':winner, 'price':price}
                self.exit_list.append({"agent":winner,"bid": price})
                return True
            elif len(self.agent_left) > 1:
                return False
            elif len(self.agent_left) == 0:
                winners = [self.exit_list[i]["agent"] for i in range(len(self.exit_list)) if self.exit_list[i]["bid"] == self.current_price]
                # randomly choose a winner
                winner = random.choice(winners)
                self.winner = {'winner':winner, 'price':self.current_price}
                return True
        elif self.rule.ascend_descend == "descend":
            if len(self.agent_left) == 1:
                winner = self.agent_left.name
                price = self.current_price
                self.winner = {'winner':winner, 'price':price}
                return True
            elif len(self.agent_left) > 1:
                ## Equal probablity to pick up one gamer
                bidder_i = random.randint(0, len(self.agent_left))
                winner = self.bid_list[bidder_i]['agent']
                return True
            elif len(self.agent_left) == 0:
                return False
            
            
class Bidder():
    '''
    This class specifies the agents
    '''
    def __init__(self, value_list, name, rule, common_value_list=[]):
        self.agent = None
        self.rule = rule
        
        self.name = f"Bidder {name}"
        self.value = value_list
        self.current_value = value_list[0]
        self.common_value = common_value_list
        self.current_common = common_value_list[0] if common_value_list is not None else 0
        self.submitted_bids = []
        self.exit_price = []
        self.profit = []
        # self.winner_profit = []
        self.winning = []
        self.history = []
        self.reasoning = []
        
    def __repr__(self):
        return repr(self.agent)

    def build_bidder(self, current_round):
        # value_prompt = f"Your value towards to the prize is {self.value[current_round]}"
        # goal_prompt = "You need to maximize your profits. If you win the bid, your profit is your value for the prize subtracting by your final bid. If you don't win, your profit is 0."
        # goal_prompt = "You need to maximize your overall profit. "
        # history_prompt = ''.join(self.history[:current_round])
        
        agent_traits = {
            # "scenario": self.rule.rule_explanation,
            # "value": value_prompt,
            # "goal": goal_prompt,
            # "history": history_prompt
        }
        self.agent = Agent(name=self.name, traits = agent_traits )
        self.current_value = self.value[current_round]
        self.current_common = self.common_value[current_round]
     
   
class Auction_CA():
    '''
    This class manages the auction process using specified agents and rules.
    '''
    def __init__(self, number_agents, rule, output_dir, timestring=None,cache=None, model='gpt-4o',temperature = 0):
        self.rule = rule        # Instance of Rule
        self.agents = []  # List of Agent instances
        self.number_agents = number_agents
        self.model= Model(model, temperature=temperature)
        self.cache = cache
        self.output_dir = output_dir
        self.timestring =timestring
        self.round_number = 0
        
        self.bids = []          # To store bid values
        self.history = []
        self.values_list = []
        self.common_value_list = []
        self.winner_list = []
        self.data_to_save = {}
        
    def draw_value(self, seed=1234):
        '''
        Determine the values for each bidder using a common value and a private part.
        '''
        # make it reproducible
        random.seed(seed)
        # Initialize the values_list as a 2D list
        self.values_list = [[{"A": 0, "B": 0} for _ in range(self.number_agents)] for _ in range(self.rule.round)]
        
        for i in range(self.rule.round):
            # Generate a common value from a range
            if self.rule.private_value == 'private':
                common_value = 0
            elif self.rule.private_value == 'common':
                common_value = random.randint(*self.rule.common_range)
            else:
                raise ValueError(f"Rule {self.rule.private_value} not allowed")
            
            self.common_value_list.append(common_value)

            # Generate a private value for each agent and sum it with the common value
            for j in range(self.number_agents):  # Now self.number_agents should be an integer
                private_part1 = random.randint(0, self.rule.private_range)
                private_part2 = random.randint(0, self.rule.private_range)
                total_value1 = common_value + private_part1
                total_value2 = common_value + private_part2
                self.values_list[i][j]["A"] = total_value1
                self.values_list[i][j]["B"] = total_value2
        print("The values for each bidder are:", self.values_list)

        
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        name_list = ["Andy", "Betty", "Charles", "David", "Ethel", "Florian"]
        for i in range(self.number_agents):
            bidder_values = [self.values_list[round_num][i] for round_num in range(self.rule.round)]
            agent = Bidder(value_list=bidder_values, common_value_list=self.common_value_list, name = name_list[i], rule=self.rule)
            agent.build_bidder(current_round=self.round_number)
            self.agents.append(agent)
            print(f"build done for Bidder {name_list[i]}")
 
    def run(self):
        # Simulate the auction process
        if self.rule.seal_clock == "clock":
            auction = Clock(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model)
            history = auction.run()
        elif self.rule.seal_clock == "seal":
            auction = SealBid(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model)
            if self.rule.type == "sequential":
                history = auction.seq_bid()
            else:
                history = auction.sim_bid()
        else:
            raise ValueError(f"Rule {self.rule.seal_clock} not allowed")
        
        # self.data_to_save[f"round_{self.round_number}"] =({"round":self.round_number, "value":self.values_list[self.round_number],"history":history})
        
        # self.winner_list.append(history["winner"]["winner"])
        # print([agent.profit[self.round_number] for agent in self.agents])
        
        self.data_to_save[f"round_{self.round_number}"] = ({"round":self.round_number, "value":self.values_list[self.round_number],"history":history, "profit":[agent.profit[self.round_number] for agent in self.agents], "common": self.common_value_list[self.round_number], "plan":[agent.reasoning[self.round_number] for agent in self.agents]})
        
    def data_to_json(self):

        save_json(self.data_to_save, f"result_{self.round_number}_{self.timestring}.json", self.output_dir)
        
    def run_repeated(self):
        self.build_bidders()
        while self.round_number < self.rule.round:
            self.run()
            self.update_bidders()
            self.round_number+=1
        self.data_to_json()
            
            
    def update_bidders(self):
        print("current bid number", self.round_number)
        
        bids_a = [agent.submitted_bids[self.round_number].get("A", 0) for agent in self.agents]
        bids_b = [agent.submitted_bids[self.round_number].get("B", 0) for agent in self.agents]
        sorted_bids_a = sorted(bids_a, reverse=True)
        sorted_bids_b = sorted(bids_b, reverse=True)
            
        if self.rule.type == "simultaneous" or self.rule.type == "sequential":
            bid_describe = (
                "All the bids for A in this round were {}".format(', '.join(map(str, sorted_bids_a))) + "\n" +
                "All the bids for B in this round were {}".format(', '.join(map(str, sorted_bids_b)))
            )
        elif self.rule.type == "menu":
            bids_ab = [agent.submitted_bids[self.round_number].get("AB", 0) for agent in self.agents]
            sorted_bids_ab = sorted(bids_ab, reverse=True)
            bid_describe = (
                "All the bids for A in this round were {}".format(', '.join(map(str, sorted_bids_a))) + "\n" +
                "All the bids for B in this round were {}".format(', '.join(map(str, sorted_bids_b))) + "\n" +
                "All the bids for AB bundle in this round were {}".format(', '.join(map(str, sorted_bids_ab)))
            )
            
        for agent in self.agents:
            bid_last_round = agent.submitted_bids[self.round_number]
                
            value_describe = f"Your value was {agent.current_value}, you bid {bid_last_round}, and your profit was {agent.profit[self.round_number]}."
            total = sum(agent.profit[:])
            total_profit_describe = f"Your total profit is {total}. "
            
            description = (
                f"In round {self.round_number}, "
                + value_describe + "\n"
                + total_profit_describe + "\n"
                + bid_describe + "\n"
                + f" Did you win A: {'Yes' if agent.winning[self.round_number]['A'] else 'No'}\n"
                + f" Did you win B: {'Yes' if agent.winning[self.round_number]['B'] else 'No'}"
                + '++++++++++'
            )
            agent.history.append(description)

            if self.round_number + 1 < self.rule.round:
                agent.build_bidder(current_round=self.round_number + 1)
        
if __name__ == "__main__":
    
    # agents = [
    #     Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds"),
    #     Agent(name = "Robin", instruction = "You are bidder 2, you need to stay for 3 round"),
    #     Agent(name = "Ben", instruction = "You are bidder 3"),
    # ]
    seal_clock='seal'
    ascend_descend=''
    price_order='second'
    private_value='common'
    open_blind='close'
    number_agents=2
    
    rule = Rule_CA(seal_clock=seal_clock, price_order=price_order, private_value=private_value,open_blind=open_blind, rounds=20, common_range=[0, 79], private_range=79, increment=1, number_agents=number_agents)
    rule.describe()
    
    model_list = ["gpt-4-1106-preview", "gpt-4-turbo", "gpt-3.5","gpt-4o"]
    sys.exit()
    # model = Model("gpt-4o", temperature=0)
    
    # q = QuestionFreeText(question_text = dedent("""\
    #     What's your goal?
    #     """), 
    #     question_name = "response"
    # )
    # survey = Survey([q])
    
    # transcript = []
    # s = Scenario({'agent_1_name': agents[0].name, 
    #               'agent_2_name': agents[1].name, 
    #               'transcript': transcript}) 
    # results = survey.by(agents[1]).by(s).run(cache = c)
    # print(results)
    # response = results.select('response').first()
    # print("====", response )
    
    ## Test Sealed bid
    # s = SealBid(agents=agents, rule=rule)
    # s.run()
    # print(s)
    
    # Test clock
    # s = Clock(agents=agents, rule=rule)
    # s.run_one_round()
    # print(s)
    
    ## Test run
    # s.run()
    # print(s)
    
    
    # Test Auction class
    ## Test draw value
    a = Auction(number_agents=3, rule=rule, output_dir=output_dir, timestring=timestring,cache=c, model ='gpt-4o', temperature=0)
    a.draw_value(seed=1456)
    
    ## Test Agent build
    a.build_bidders()
    # print(a.agents)
    
    ## Test on running
    a.run()
    c.write_jsonl("running.jsonl")
    
    ## Test on the descend clock
    #the asking prompt
    
    ## Test for repeated game
    
    ## Test for Scenario
    # what kind of infor to put into the scenatrio
    # what's the difference between putting infor into the question and the scenatio?
    
    ## Test prompt structure
    ## how to input the prompts
    
    # auction = Auction(agents, rule=rule)