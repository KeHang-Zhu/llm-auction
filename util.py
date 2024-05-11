from textwrap import dedent
from itertools import cycle
import random
import os

from edsl import Agent, Scenario, Survey
from edsl.data import Cache
from edsl.Base import Base
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
    def __init__(self, seal_open, ascend_descend, private, price_order):
        self.seal_open = seal_open
        self.ascend_descend = ascend_descend
        self.private = private
        self.order = price_order
        
        ## Rule prompt
        prompt_mixin = PromptMixin()
        # self.rule_explanation = prompt_mixin.generate_prompt(f"{self.seal_open}_{self.ascend_descend}_{self.private}.txt", template_dir = templates_dir)
        ## Bid asking prompt
        # self.asking_prompt = f"Do you want to "

    def describe(self):
        # Provides a description of the auction rule
        print(f"Auction Type: {self.seal_open}, Bidding Order: {self.ascend_descend}, Value Type: {self.private}")


class Bidder(Agent):
    '''
    This class defines bidder from the base class Agent.
    '''
    def __init__(self, name, rule):
        self.system_prompt = rule.rule_explanation
        self.agent = Agent(name=name, instruction=self.system_prompt)
    


class SealBid():
    def __init__(self, agents, rule):
        self.bid_list = []
        self.rule = rule
        self.agents = agents
        self.context = ...#rule.context
        self.scenario = Scenario({'agent_1_name': agents[0].name, 
                  'agent_2_name': agents[1].name}) 
        self.winner = None
        
    def __repr__(self):
        return f'SealBid(bid_list={self.bid_list})'
    
    def run(self):
        '''run for one round'''
        q_bid = QuestionNumerical(
            question_name = "q_bid",
            question_text = "how much do you like to bid?(in $USD)"#self.context + "."
        )

        for agent in self.agents:
            survey = Survey(questions = [q_bid])
            result = survey.by(self.scenario).by(agent).run(progress_bar=True)
            response = result.select("q_bid").to_list()[0]
            self.bid_list.append({"agent":agent.name,"bid": response})
            
            
    def declare_winner_and_price(self):
        '''Sort the bid list by the 'bid' key in descending order to find the highest bids'''
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
    

class Clock():
    def __init__(self, agents, rule, change =5):
        self.current_bid = []
        self.bid_list = []
        self.agents = agents
        self.change = change
        self.rule = rule
        self.scenario = Scenario({'agent_1_name': agents[0].name, 
                  'agent_2_name': agents[1].name}) 
        self.transcript = []
        self.current_price = 0
        # all the agents in the game
        self.agent_left = agents
        self.winner = None
    
    def __repr__(self):
        return f'SealBid(bid_list={self.bid_list})'
        
    def dynamic(self):
        if self.rule.order == "ascending":
            self.current_price +=self.change
        else:
            self.current_price -=self.change
    
    def run_one_round(self):
        '''run for one round'''
        ## calculate the next clock price
        self.dynamic()
        
        ## update the shared information
        self.transcript.append(self.share_information())

        for agent in self.agent_left:
            other_agent_names = ', '.join([a.name for a in self.agent_left if a is not agent])
            
            q_bid = QuestionYesNo(
                question_name = "q_bid",
                question_text = dedent("""\
            You are {{ agent_name }}. 
            You are bidding with {{ other_agent_names}}.
            The transcript so far is: 
            {{ transcript }}
            It is your turn to bid.
            Do you want to stay or drop out at the current price {{current_price}}
            """), 
            )
            scenario = Scenario({"agent_name": agent.name, "other_agent_names": other_agent_names, "transcript": self.transcript, "current_price": self.current_price})
            
            survey = Survey(questions = [q_bid])
            result = survey.by(scenario).by(agent).run(progress_bar=True)
            response = result.select("q_bid").to_list()[0]
            self.bid_list.append({"agent":agent.name,"bid": response})
            

    def run(self):
        '''Run the clock until the ending condition'''
        while self.declear_winner_and_price() is False:
            self.run_one_round()
            
        self.declear_winner_and_price()
             
    
    def share_information(self):
        if self.rule.seal_open == "open":
            return f'all the biddings are {self.bid_list}'
        elif self.rule.info == "blind":
            return None

    
    def declear_winner_and_price(self):
        if len(self.bid_list) == 1:
            winner = self.bid_list[0]['name']
            price = self.bid_list[0]['price']
            self.winner = {'winner':winner, 'price':price}
            return True
        
        elif len(self.bid_list) > 1:
            if self.response.lower() == 'no':
                self.agent_left.remove(agent)
            return False
        elif len(self.bid_list) == 0:
            print("No winner")
            return True
            

class Auction():
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
        for _ in range(self.number_agents):  # Now self.number_agents should be an integer
            private_part = random.randint(0, private_range)
            total_value = common_value + private_part
            self.values_list.append(total_value)
        print("The values for each bidder are:", self.values_list)

        
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        for i in range(self.number_agents): 
            rule_prompt = None#self.rule.rule_explanation
            value_prompt = f"Your value towards to item is {self.values_list[i]}"
            
            agent_traits = {
                "value": value_prompt,
            }
            agent = Agent(name=f"Bidder {i+1}", traits = agent_traits, instruction=rule_prompt)
            self.agents.append(agent)
 
    def run(self, temperature):
        # Simulate the auction process
        if self.rule.type == "clock":
            auction = Clock(agents=self.agents, rule=self.rule)
            auction.run() 
        elif self.rule.type == "sealed":
            auction = SealBid(agents=self.agents, rule=self.rule)
            auction.run()

    def results(self):
        # Analyze and print auction results
        if self.bids:
            highest_bid = max(self.bids)
            winner = [agent for agent in self.agents if agent.last_bid == highest_bid][0]
            return f"The winner is {winner.name} with a bid of {highest_bid}"
        else:
            return "No bids were placed."

    


if __name__ == "__main__":
    
    agents = [
        Agent(name = "John", instruction = "You are bidder 1, you need to quit after 2 rounds"),
        Agent(name = "Robin", instruction = "You are bidder 2, you need to quit after 1 round"),
        Agent(name = "Ben", instruction = "You are bidder 3"),
    ]
    
    rule = Rule(seal_open='open',  ascend_descend='private',price_order='ascending', private='common value')
    rule.describe()
    
    model = "gpt-4-turbo"
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
    
    ## Test clock
    # s = Clock(agents=agents, rule=rule)
    # s.run_one_round()
    # print(s)
    
    
    # Test Auction class
    ## Test draw value
    # a = Auction(number_agents=3, rule=rule)
    # a.draw_value()
    ## Test Agent build
    # a.build_bidders()
    # print(a.agents)
    
    ## Test on public info
    
    ## Test on public info
    
    # auction = Auction(agents, rule=rule)