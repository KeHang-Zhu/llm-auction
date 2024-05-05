from textwrap import dedent
from itertools import cycle
import random
import os

from edsl.data import Cache
from edsl.Base import Base
from edsl import Agent, Scenario, Survey
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionNumerical

from Prompting import PromptMixin

current_script_path = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_script_path, './prompt_templates')

c = Cache()  

class Rule:
    '''
    This class defines different auction rules and their behaviors.
    '''
    def __init__(self, seal_clock, ascend_descend, private_open, price_order):
        self.seal_clock = seal_clock
        self.ascend_descend = ascend_descend
        self.private_open = private_open
        self.price_order = price_order
        
        ## Rule prompt
        prompt_mixin = PromptMixin()
        self.rule_explanation = prompt_mixin.generate_prompt(f"{self.seal_clock}_{self.ascend_descend}_{self.private_open}.txt", template_dir = templates_dir)
        ## Bid asking prompt
        # self.asking_prompt = f"Do you want to "

    def describe(self):
        # Provides a description of the auction rule
        pass
        # return f"Auction Type: {self.style}, Bidding Order: {self.order}, Value Type: {self.value_type}"


class Bidder(Agent):
    '''
    This class defines bidder from the base class Agent.
    '''
    def __init__(self, name, rule):
        self.system_prompt = rule.rule_explanation
        self.agent = Agent(name=name, instruction=self.system_prompt)
    


class SealBid(Base, Rule):

    def __init__(self, agents, rule):
        self.bid_list = []
        self.rule = rule
        self.agents = agents
        self.context = rule.context
        self.scenario = Scenario() 
    
    def run(self):
        '''run for one round'''
        q_bid = QuestionNumerical(
            question_name = "q_bid",
            question_text = self.context + "(in $USD)."
        )

        for agent in self.agents:
            survey = Survey(questions = q_bid)
            result = survey.by(self.scenario).by(agent).run(progress_bar=True)
            self.bid_list.append({"agent":agent.name,"bid": result})
            
            
    def declare_winner_and_price(self):
        ''' Sort the bid list by the 'bid' key in descending order to find the highest bids'''
        sorted_bids = sorted(self.bid_list, key=lambda x: x['bid'], reverse=True)

        if self.rule.price == "first":
            if len(sorted_bids) > 0:
                winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        elif self.rule.price == "second":
            if len(sorted_bids) > 1:
                winner = sorted_bids[1]["agent"]
                price = sorted_bids[1]["bid"]
        elif self.rule.price == "third":
            if len(sorted_bids) > 2:
                winner = sorted_bids[2]["agent"]
                price = sorted_bids[2]["bid"]

        return winner, price
    
class Clock(Base, Rule):
    def __init__(self, agents, rule, change =1):
        self.current_bid = []
        self.bid_list = []
        self.agents = agents
        self.change = change
        self.rule = rule
        self.scenario = Scenario() 
        self.transcript = []
        
    def dynamic(self, price_next):
        if self.rule.order == "ascending":
            price_next +=self.change
        else:
            price_next -=self.change
            
        return price_next
    
    def run_one_round(self, current_price, agent_left):
        '''run for one round'''
        ## calculate the next clock price
        clock_price =  self.dynamic(current_price)
        
        ## update the shared information
        self.transcript.append(self.share_information())
        
        q_bid = QuestionYesNo(question_text = dedent(f"""
            You are {{ agent_name }}. 
            You are bidding with {{ other_agent_name }}.
            The transcript so far is: 
            { self.transcript }
            It is your turn to bid.
            Do you want to stay or drop out at the current price {clock_price}      
            """), 
            question_name = "stay_or_exit")

        for agent in self.agents:
            survey = Survey(questions = q_bid)
            result = survey.by(self.scenario).by(agent).run(progress_bar=True)
            self.bid_list.append({"agent":agent.name,"decision": result})
            

    def run(self, temperature):
        
        # Take out the bidders that have dropped out
        
        # Run the clock until the ending condition
        

        for agent in cycle(self.agents):
            bid = agent.bid(current_bid, temperature)
            if bid is not None and bid < current_bid:
                self.bids.append(bid)
                current_bid = bid
            else:
                break  # Assuming bidding stops if no new bid is lower
            
    
    def share_information(self):
        if self.rule.info == "open":
            return f'all the biddings are {self.bid_list}'
        elif self.rule.info == "blind":
            return None
    
    def check_ending(self):
        if len(self.bid_list) > 1:
            return False
        
        return True
    
    def declear_winner_and_price(self):
        if len(self.bid_list) == 1:
            winner = ...
            price = self.bid_list[0]
            return {'winner':winner, 'price':price}
        elif len(self.bid_list) == 0:
            return "No winner"
            

class Auction(Base, Rule):
    '''
    This class manages the auction process using specified agents and rules.
    '''
    def __init__(self, number_agents, rule):
        self.agents = []  # List of Agent instances
        self.number_agents = number_agents
        self.rule = rule        # Instance of Rule
        self.bids = []          # To store bid values
        self.history = []
        self.values_list = []
        
    def draw_value(self, common_range=(10, 100), private_range=20):
        '''
        Determine the values for each bidder using a common value and a private part.
        '''
        # Generate a common value from a range
        common_value = random.randint(*common_range)

        # Generate a private value for each agent and sum it with the common value
        for _ in range(self.number_agents):
            private_part = random.randint(0, private_range)
            total_value = common_value + private_part
            self.values_list.append(total_value)

        print("The values for each bidder are:", self.values_list)
        
    
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        for i in range[0, self.number_agents]:
            rule_prompt = self.rule.rule_explanation
            value_prompt = f"Your value towards to item is {self.values_list[i]}"
            
            agent_traits = {
                "value": value_prompt,
            }
            agent = Agent(name=f"Bidder {i+1}", traits = agent_traits, instruction=rule_prompt)
            self.agents.append(agent)
 
    def run(self, temperature):
        # Simulate the auction process
        if self.rule.type == "clock":
            auction = Clock(temperature)
            auction.run() 
        elif self.rule.type == "sealed":
            auction = SealBid(temperature)
            auction.run()

    def results(self):
        # Analyze and print auction results
        if self.bids:
            highest_bid = max(self.bids)
            winner = [agent for agent in self.agents if agent.last_bid == highest_bid][0]
            return f"The winner is {winner.name} with a bid of {highest_bid}"
        else:
            return "No bids were placed."

    

