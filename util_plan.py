import textwrap
from textwrap import dedent
from itertools import cycle
import random
import json
import os
import sys
from edsl import Model
from edsl import Agent, Scenario, Survey
from edsl.data import Cache
from edsl.Base import Base
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionNumerical
from jinja2 import Template
import re

current_script_path = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_script_path, './rule_template/V10/')
prompt_dir = os.path.join(current_script_path, './Prompt/')

c = Cache()  

def save_json(data, filename, directory):
    """Save data to a JSON file in the specified directory."""
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    return file_path

class Rule_plan:
    '''
    This class defines different auction rules and their behaviors.
    '''
    def __init__(self, seal_clock,  private_value, open_blind, rounds, 
                 ascend_descend="ascend",
                 price_order = "second",
                 common_range=[10, 80], private_range=20, increment=1, number_agents=3, special_name="", start_price=0, turns=20):
        self.seal_clock = seal_clock
        self.ascend_descend = ascend_descend
        self.private_value = private_value
        self.open_blind = open_blind
        self.price_order = price_order
        self.round = rounds
        self.turns = turns
        self.common_range = common_range
        self.private_range = private_range
        self.increment = increment
        self.number_agents = number_agents
        self.start_price= start_price
        
        ## Rule prompt
        # intro_string = Prompt.from_txt(os.path.join(templates_dir,"intro.txt"))
        # intro = intro_string.render({"n":self.round})

        # value_explain_string = Prompt.from_txt(os.path.join(templates_dir,f"intro_{self.private_value}.txt"))
        # value_explain = value_explain_string.render({"increment":self.increment,"common_low":self.common_range[0], "common_high":self.common_range[1],"private":self.private_range, "num_bidders": self.number_agents-1})
        if special_name:
            game_type_string = Prompt.from_txt(os.path.join(templates_dir,special_name))
            game_type = game_type_string.render({
                "item_description": "256GB IPhone 16 pro",
                "item_condition": "used",
                "start_price":  0,
                "num_rounds": self.turns, 
                "bid_increment":self.increment
            })
        else:
            if self.seal_clock == 'clock':
                game_type_string = Prompt.from_txt(os.path.join(templates_dir,f"{self.ascend_descend}_{self.private_value}_{self.open_blind}.txt"))
            elif self.seal_clock == 'seal':
                game_type_string = Prompt.from_txt(os.path.join(templates_dir,f"{self.price_order}_price_{self.private_value}.txt"))
            game_type = game_type_string.render({"increment":self.increment,"min_price":self.common_range[0],"max_price":self.common_range[1]+self.private_range, "common_low":self.common_range[0], "common_high":self.common_range[1],"num_bidders": self.number_agents-1, "private":self.private_range, "n":self.round})
        
        # if self.round > 1:
        #     multi_string = Prompt.from_txt(os.path.join(templates_dir,"multi.txt"))
        #     ending = multi_string.render({"n":self.round})
        # else:
        #     ending = ''
        
        ## Combine the rule prompt
        self.rule_explanation =  game_type
        
        persona_str = Prompt.from_txt(os.path.join(prompt_dir,"persona.txt"))
        self.persona = str(persona_str.render({}))

        ## Bid asking prompt
        if self.seal_clock == "seal":
            ask_str = Prompt.from_txt(os.path.join(prompt_dir,"asking_sealed.txt"))
            self.asking_prompt = str(ask_str.render({}))
        elif self.seal_clock == "clock":
            if self.ascend_descend == "ascend":
                self.asking_prompt = "Do you want to stay in the bidding?"
            elif self.asking_prompt == "descend":
                self.asking_prompt = "Do you want to accept the current price?"
                

    def describe(self):
        # Provides a description of the auction rule
        print(f"Auction Type: {self.seal_clock}, \nBidding Order: {self.ascend_descend}, \nValue Type: {self.private_value}, \n Information Type: {self.open_blind}, \n price order: {self.price_order}")


class SealBid():
    def __init__(self, agents, rule, model, cache= c, history=None):
        
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
    
    def parse_bid(self, text):
        ##  <BID>20<\BID>
        pattern = r"<BID>.*?(\d+).*?<\\?BID>"
        ##  <BID>20</BID>
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        
        if match:
            try:
                # Extract and convert the matched bid value to float
                quantity = float(match.group(1).strip())
                return quantity
            except ValueError:
                # Handle cases where the value isn't a valid number
                raise ValueError("Invalid bid value")
        else:
            # Return a message if no valid match is found
            raise ValueError("Invalid bid value")

    
    def run(self):
        '''run for one round'''

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
            instruction = str(instruction_str.render({"name":agent.name, "other_agent_names": other_agent_names}))

            general_prompt = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" 

            if len(agent.reasoning) == 0:
                elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_first.txt"))
                prompt_elicit_plan = str(elicit_plan.render({}))

                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = general_prompt +  prompt_elicit_plan
                )
                survey = Survey(questions = [q_plan])
                result = survey.by(agent.agent).by(self.model).run(cache = self.cache)
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan)
                
                elicit_bid = Prompt.from_txt(os.path.join(prompt_dir,"bid_first.txt"))
                prompt_elicit_bid = str(elicit_bid.render({"current_value":agent.current_value, "plan": plan}))
                
                # Initialize bid and a retry mechanism
                retry_attempts = 3
                attempt = 0
                bid = None
                format_warning = ''
                while attempt < retry_attempts:
                    try:
                        # Run the survey and fetch the result
                        q_bid = QuestionFreeText(
                            question_name="q_bid",
                            question_text=general_prompt + prompt_elicit_bid + format_warning
                        )
                        result = self.model.simple_ask(q_bid)
                        bid_str= result['choices'][0]['message']['content']
                        print(bid_str)
                        bid = self.parse_bid(bid_str)
                        break  # Exit loop if bid is successfully processed
                    except (ValueError, TypeError) as e:
                        # Handle conversion errors or other issues
                        print(f"Error processing bid: {e}. Retrying ({attempt + 1}/{retry_attempts})...")
                        attempt += 1
                        format_warning = "Wrong format. You MUST follow the output format!"
                        continue

                if bid is None or attempt == retry_attempts:
                    raise RuntimeError("Failed to process the bid after multiple attempts.")


            else:
                last_round = agent.history[-1]

                reflection = Prompt.from_txt(os.path.join(prompt_dir,"reflection.txt"))
                prompt_reflection = str(reflection.render({"last_round":last_round}))

                q_counterfact = QuestionFreeText(
                    question_name = "q_counterfact",
                    question_text = general_prompt+ prompt_reflection
                )
                result = self.model.simple_ask(q_counterfact)
                counterfact= result['choices'][0]['message']['content']
                # print("=========================== \n", counterfact)
                
                history = agent.history
                reasoning = agent.reasoning
                max_length = max(len(history), len(reasoning))
                history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i] for i in range(max_length)])
                # previous_plan = agent.reasoning[-1]
                elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_after_reflec.txt"))
                prompt_elicit_plan = str(elicit_plan.render({"history": history_prompt, "counterfact":counterfact}))
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = general_prompt + prompt_elicit_plan
                )
            
                # print(q_plan)
                # result = self.model.simple_ask(q_plan)
                survey = Survey(questions = [q_plan])
                result = survey.by(agent.agent).by(self.model).run(cache = self.cache)
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan, "====================\n")
                
                elicit_bid = Prompt.from_txt(os.path.join(prompt_dir,"bid_after_reflec.txt"))
                prompt_elicit_bid = str(elicit_bid.render({"counterfact": counterfact,"current_value": agent.current_value, "plan": plan}))


                retry_attempts = 3
                attempt = 0
                bid = None
                format_warning = ''
                while attempt < retry_attempts:
                    try:
                        # Run the survey and fetch the result
                        q_bid = QuestionFreeText(
                            question_name = "q_bid",
                            question_text =  general_prompt + prompt_elicit_bid + format_warning
                            )
                        result = self.model.simple_ask(q_bid)
                        bid_str= result['choices'][0]['message']['content']
                        print(bid_str)
                        bid = self.parse_bid(bid_str)
                        break  # Exit loop if bid is successfully processed
                    except (ValueError, TypeError) as e:
                        # Handle conversion errors or other issues
                        print(f"Error processing bid: {e}. Retrying ({attempt + 1}/{retry_attempts})...")
                        attempt += 1
                        format_warning = "Wrong format. You MUST follow the output format!"
                        continue

                if bid is None or attempt == retry_attempts:
                    raise RuntimeError("Failed to process the bid after multiple attempts.")

            # print(response)

            agent.reasoning.append(plan)
            self.bid_list.append({"agent":agent.name,"bid": bid})
            agent.submitted_bids.append(bid)
            
        print(self.bid_list, '\n Value list:',[agent.current_value for agent in self.agents])
        self.declare_winner_and_price()
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}
    
            
    def declare_winner_and_price(self):
        '''Sort the bid list by the 'bid' key in descending order to find the highest bids'''
        sorted_bids = sorted(self.bid_list, key=lambda x: float(x['bid']), reverse=True)

        if self.rule.price_order == "first":
            if len(sorted_bids) > 0:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        elif self.rule.price_order == "second":
            if len(sorted_bids) > 1:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[1]["bid"]
        elif self.rule.price_order == "third":
            if len(sorted_bids) > 2:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[2]["bid"]
        elif self.rule.price_order == "allpay":
            if len(sorted_bids) > 0:
                same_bids = [bid for bid in sorted_bids if bid["bid"] == sorted_bids[0]["bid"]]
                winner = random.choice(same_bids)["agent"]
                # winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        else: 
            raise ValueError(f"Rule {self.rule.price_order} not allowed")
        
        self.winner = {'winner':winner, 'price':price}
        for agent in self.agents:
            ## implement the all pay auction
            if self.rule.price_order == "allpay":
                for bid in self.bid_list:
                    if bid["agent"] == agent.name:
                        price = bid["bid"]
                agent.profit.append(agent.current_value - price)
                if agent.name == winner:
                    agent.winning.append(True)
                else:
                    agent.winning.append(False)
            else:
                if agent.name == winner:
                    if self.rule.private_value == "private":
                        agent.profit.append(agent.current_value - float(price))
                    elif self.rule.private_value == "common":
                        agent.profit.append(agent.current_common - float(price))
                    agent.winning.append(True)
                else:
                    agent.profit.append(0)
                    agent.winning.append(False)
    
class Clock():
    def __init__(self, agents, rule, model, cache=c, history=None):
        
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
    
    def run_one_clock(self, counterfact=None):
        '''run for one round'''
        self.exit_number = 0
        print("===========",self.current_price)
        agent_in_play = self.agent_left[:]
        
        for agent in agent_in_play:
            other_agent_names = ', '.join([a.name for a in agent_in_play if a is not agent])
            instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
            instruction = str(instruction_str.render(
                {"name":agent.name, "other_agent_names": other_agent_names})
                )

            if counterfact is None:
                elicit_bid = Prompt.from_txt(os.path.join(prompt_dir,"bid_clock.txt"))
                prompt_elicit_bid = str(elicit_bid.render(
                    {"current_value": agent.current_value, 
                    "transcript": self.transcript, 
                    "urrent_price":self.current_price, 
                    "plan": agent.reasoning[-1]})
                    )
            else:
                elicit_bid = Prompt.from_txt(os.path.join(prompt_dir,"bid_clock_reflec.txt"))
                prompt_elicit_bid = str(elicit_bid.render(
                    {"counterfact": counterfact,
                     "current_value": agent.current_value, 
                    "transcript": self.transcript, 
                    "urrent_price":self.current_price, 
                    "plan": agent.reasoning[-1]})
                    )
                
            general_prompt = instruction + str(self.rule.rule_explanation) + prompt_elicit_bid

            q_bid = QuestionYesNo(
                question_name = "q_bid",
                question_text = general_prompt,
            )
            # print(instruction)
            # print(q_bid)
            # print(agent)
            # scenario = Scenario()
            # agent = Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds")
            survey = Survey(questions = [q_bid])
            result = survey.by(agent.agent).by(self.model).run(cache = self.cache)
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

        ## elicit agent plans
        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction_str = Prompt.from_txt(os.path.join(prompt_dir,"instruction.txt"))
            instruction = str(instruction_str.render({"name":agent.name, "other_agent_names": other_agent_names}))

            general_prompt = instruction + self.rule.persona + str(self.rule.rule_explanation) + "\n" 
            if len(agent.reasoning) == 0:
                elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_first.txt"))
                prompt_elicit_plan = str(elicit_plan.render({}))

                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = general_prompt +  prompt_elicit_plan
                )
                survey = Survey(questions = [q_plan])
                result = survey.by(agent.agent).by(self.model).run(cache = self.cache)
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan)
                agent.reasoning.append(plan)

                stop_condition = False
                while stop_condition is False:
                    self.bid_list = []
                    self.run_one_clock(reflection = None)
                    print(self.clock+1, '+++++done')
                    self.clock +=1
                    stop_condition = self.declear_winner_and_price()
                    ## calculate the next clock price
                    self.dynamic()
                    print(self.__repr__())

            else:
                last_round = agent.history[-1]

                reflection = Prompt.from_txt(os.path.join(prompt_dir,"reflection.txt"))
                prompt_reflection = str(reflection.render({"last_round":last_round}))

                q_counterfact = QuestionFreeText(
                    question_name = "q_counterfact",
                    question_text = general_prompt+ prompt_reflection
                )
                result = self.model.simple_ask(q_counterfact)
                counterfact= result['choices'][0]['message']['content']
                # print("=========================== \n", counterfact)
                
                history = agent.history
                reasoning = agent.reasoning
                max_length = max(len(history), len(reasoning))
                history_prompt = ''.join([history[i] +" your plan for this round is: "+ reasoning[i] if i < len(history) and i < len(reasoning) else history[i] if i < len(history) else reasoning[i] for i in range(max_length)])
                # previous_plan = agent.reasoning[-1]
                elicit_plan = Prompt.from_txt(os.path.join(prompt_dir,"plan_after_reflec.txt"))
                prompt_elicit_plan = str(elicit_plan.render({"history": history_prompt, "counterfact":counterfact}))
                q_plan = QuestionFreeText(
                    question_name = "q_plan",
                    question_text = general_prompt + prompt_elicit_plan
                )
            
                # print(q_plan)
                # result = self.model.simple_ask(q_plan)
                survey = Survey(questions = [q_plan])
                result = survey.by(agent.agent).by(self.model).run(cache = self.cache)
                plan = result.select("q_plan").to_list()[0]
                # plan= result['choices'][0]['message']['content']
                print(plan, "====================\n")

                agent.reasoning.append(plan)

                stop_condition = False
                while stop_condition is False:
                    self.bid_list = []
                    self.run_one_clock(reflection = reflection)
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
     
   
class Auction_plan():
    '''
    This class manages the auction process using specified agents and rules.
    '''
    def __init__(self, number_agents, rule, output_dir, timestring=None,cache=c, model='gpt-4o',temperature = 0):
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
        self.values_list = [[0 for _ in range(self.number_agents)] for _ in range(self.rule.round)]
        
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
                private_part = random.randint(0, self.rule.private_range)
                total_value = common_value + private_part
                self.values_list[i][j] = total_value
        print("The values for each bidder are:", self.values_list)

        
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        name_list = ["Andy", "Betty", "Charles", "David", "Ethel", "Florian"]
        for i in range(self.number_agents):
            bidder_values = [self.values_list[round_num][i] for round_num in range(self.rule.round)]
            agent = Bidder(value_list=bidder_values, common_value_list=self.common_value_list, name = name_list[i], rule=self.rule)
            agent.build_bidder(current_round=self.round_number)
            self.agents.append(agent)
 
    def run(self):
        # Simulate the auction process
        if self.rule.seal_clock == "clock":
            auction = Clock(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model)
            history = auction.run()
        elif self.rule.seal_clock == "seal":
            auction = SealBid(agents=self.agents, rule=self.rule, cache=self.cache, history=self.history, model=self.model)
            history = auction.run()
        else:
            raise ValueError(f"Rule {self.rule.seal_clock} not allowed")
        
        
        self.winner_list.append(history["winner"]["winner"])
        print([agent.profit[self.round_number] for agent in self.agents])
        
        self.data_to_save[f"round_{self.round_number}"] = ({"round":self.round_number, "value":self.values_list[self.round_number],"history":history, "profit":[agent.profit[self.round_number] for agent in self.agents], "common": self.common_value_list[self.round_number], "plan":[agent.reasoning[self.round_number] for agent in self.agents]})
        
    def data_to_json(self):

        print(f"open the file {self.output_dir}, start to write the results")
        print(self.data_to_save)
        save_json(self.data_to_save, f"result_{self.round_number}_{self.timestring}.json", self.output_dir)
        print("Write done!")
        
    def run_repeated(self):
        self.build_bidders()
        while self.round_number < self.rule.round:
            self.run()
            if self.round_number < self.rule.round-1:
                self.update_bidders()
            self.round_number+=1
        self.data_to_json()
            
            
    def update_bidders(self):
        #Following each auction, each subject observes a results summary, containing all submitted bids or exit prices, respectively, her own profit, and the winner’s profit
        print("current bid number", self.round_number)
        if self.rule.seal_clock == "seal":
            bids = [float(agent.submitted_bids[self.round_number]) for agent in self.agents]
            sorted_bids = sorted(bids, reverse=True)
            bid_describe = "All the bids for this round were {}".format(', '.join(map(str, sorted_bids)))
            if self.rule.price_order == "second":
                bid_describe += f". The highest bidder won with a bid of {sorted_bids[0]} and paid {sorted_bids[1]}."
            elif self.rule.price_order == "first":
                bid_describe += f". The highest bidder won with a bid of {sorted_bids[0]} and would’ve preferred to bid {float(sorted_bids[1]) + 1}."
        elif self.rule.seal_clock == "clock":
            bids = [agent.exit_price[self.round_number] for agent in self.agents]
            sorted_bids = sorted(bids, reverse=True)
            bid_describe = "All the exit prices for this round were {}".format(', '.join(map(str, sorted_bids)))


        # if self.winner_list[self.round_number] == "NA":
        #     winner_profit = 0
        # else:
        winner_profit = next(agent.profit[self.round_number] for agent in self.agents if agent.name == self.winner_list[self.round_number])
        
        # for agent in self.agents:
        #     if self.rule.seal_clock == "seal":
        #         bid_last_round = agent.submitted_bids[self.round_number]
        #     elif self.rule.seal_clock == "clock":
        #         bid_last_round = agent.exit_price[self.round_number] 
                
        #     value_describe = f"Your value was {agent.current_value}. And you bid {bid_last_round}. "
        #     if self.rule.seal_clock == "seal":
        #         reasoning_describe = f"Your reasoning for your decision was '{agent.reasoning[self.round_number]}' "
        #     else:
        #         reasoning_describe = ""
        #     total = sum(agent.profit[:])
        #     profit_describe = f"Your profit was {agent.profit[self.round_number]} and winner's profit was {winner_profit}. Your total profit is {total} \n"
        #     ## combine into history
        #     description = f"In round {self.round_number}, " + value_describe + profit_describe + reasoning_describe + bid_describe
            
        for agent in self.agents:
            if self.rule.private_value == "private":
                if self.rule.seal_clock == "seal":
                    bid_last_round = agent.submitted_bids[self.round_number]
                elif self.rule.seal_clock == "clock":
                    bid_last_round = agent.exit_price[self.round_number]
                value_describe = f"Your value was {agent.current_value}, you bid {bid_last_round}, and your profit was {agent.profit[self.round_number]}."
                total = sum(agent.profit[:])
                total_profit_describe = f"Your total profit is {total}. "
                #Combine the personal results and group results
                description = (
                    f"In round {self.round_number}, "
                    + value_describe + "\n"
                    + total_profit_describe + "\n"
                    + bid_describe + f" The winner's profit was {winner_profit}."
                    + f" Did you win the auction: {'Yes' if agent.winning[self.round_number] else 'No'}"
                    + '++++++++++'
                )
            elif self.rule.private_value == "common":
                if self.rule.seal_clock == "seal":
                    bid_last_round = agent.submitted_bids[self.round_number]
                elif self.rule.seal_clock == "clock":
                    bid_last_round = agent.exit_price[self.round_number]
                value_describe = f"Your (perceived) total value was {agent.current_value}, you bid {bid_last_round}, the (true) common value of the prize was {agent.current_common}, and your profit (based on the true value of the prize) was {agent.profit[self.round_number]}."
                total = sum(agent.profit[:])
                total_profit_describe = f"Your total profit is {total}. "
                #Combine the personal results and group results
                description = (
                    f"In round {self.round_number}, "
                    + value_describe + "\n"
                    + total_profit_describe + "\n"
                    + bid_describe + f" The winner's profit was {winner_profit}."  + "\n"
                    + (f"Your reasoning for your decision was '{agent.reasoning[self.round_number]}' " if self.rule.seal_clock == "seal" else "")
                )
            agent.history.append(description)
            # print(agent.history)
            if self.round_number+1 < self.rule.round:
                agent.build_bidder(current_round=self.round_number+1)


        
        
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
    
    rule = Rule_plan(seal_clock=seal_clock, price_order=price_order, private_value=private_value,open_blind=open_blind, rounds=20, common_range=[0, 79], private_range=79, increment=1, number_agents=number_agents)
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