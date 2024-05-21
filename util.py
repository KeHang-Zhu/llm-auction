import textwrap
from textwrap import dedent
from itertools import cycle
import random
import json
import os
from edsl import shared_globals
from edsl import Model
from edsl import Agent, Scenario, Survey
from edsl.data import Cache
from edsl.Base import Base
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionNumerical


current_script_path = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(current_script_path, './rule_template')

c = Cache()  

def save_json(data, filename, directory):
    """Save data to a JSON file in the specified directory."""
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    return file_path

class Rule:
    '''
    This class defines different auction rules and their behaviors.
    '''
    def __init__(self, seal_clock, ascend_descend, private_value, price_order, open_blind):
        self.seal_clock = seal_clock
        self.ascend_descend = ascend_descend
        self.private_value = private_value
        self.open_blind = open_blind
        self.price_order = price_order
        
        ## Rule prompt
        intro = Prompt.from_txt(os.path.join(templates_dir,"intro.txt"))
        value_explain = Prompt.from_txt(os.path.join(templates_dir,f"value_{self.private_value}.txt"))
        if self.seal_clock == 'clock':
            game_type = Prompt.from_txt(os.path.join(templates_dir,f"{self.ascend_descend}.txt"))
        elif self.seal_clock == 'seal':
            game_type = Prompt.from_txt(os.path.join(templates_dir,f"{self.price_order}_price.txt"))
        self.rule_explanation = intro  + value_explain + game_type
        # print(self.rule_explanation)
        
        ## Bid asking prompt
        if self.seal_clock == "seal":
            self.asking_prompt = "how much do you like to bid?(in $USD)"
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
        
        self.scenario = Scenario({
            'agent_1_name': agents[0].name, 
            'agent_2_name': agents[1].name, 
            'the history of this game': self.history
            }) 
        
        ## for bidding 
        self.bid_list = []
        self.winner = None
        
        
    def __repr__(self):
        return f'Sealed Bid Auction: (bid_list={self.bid_list})'
    
    def run(self):
        '''run for one round'''

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            instruction = f"""{self.rule.rule_explanation}\n
            You are {agent.name}. 
            You are bidding with { other_agent_names}.
            """
            q_bid = QuestionNumerical(
            question_name = "q_bid",
            question_text = instruction+ self.rule.asking_prompt
        )

            survey = Survey(questions = [q_bid])
            result = survey.by(agent).by(self.model).run(cache = self.cache)
            response = result.select("q_bid").to_list()[0]
            self.bid_list.append({"agent":agent.name,"bid": response})
            
        print(self.bid_list)    
        self.declare_winner_and_price()
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}
            
            
    def declare_winner_and_price(self):
        '''Sort the bid list by the 'bid' key in descending order to find the highest bids'''
        sorted_bids = sorted(self.bid_list, key=lambda x: x['bid'], reverse=True)

        if self.rule.price_order == "first":
            if len(sorted_bids) > 0:
                winner = sorted_bids[0]["agent"]
                price = sorted_bids[0]["bid"]
        elif self.rule.price_order == "second":
            if len(sorted_bids) > 1:
                winner = sorted_bids[0]["agent"]
                price = sorted_bids[1]["bid"]
        elif self.rule.price_order == "third":
            if len(sorted_bids) > 2:
                winner = sorted_bids[0]["agent"]
                price = sorted_bids[2]["bid"]
        else: 
            raise ValueError(f"Rule {self.rule.price_order} not allowed")
        
        self.winner = {'winner':winner, 'price':price}
    

class Clock():
    def __init__(self, agents, rule, model, cache=c,change =5, starting_price=0, history=None):
        
        ## for setting up stage
        self.rule = rule
        self.agents = agents
        self.change = change
        self.current_price = starting_price
        self.model = model
        self.cache = cache
        ## For repeated game:
        self.history = history
        
        if self.rule.ascend_descend == "ascend":
            self.agent_left = agents
        elif self.rule.ascend_descend == "descend":
            self.agent_left = []
        
        # For bidding storage
        self.round = 0
        self.current_bid = []
        self.bid_list = []    
        self.transcript = []
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
    
    def run_one_round(self):
        '''run for one round'''
        ## calculate the next clock price
        self.dynamic()
        print("===========",self.current_price)
        agent_in_play = self.agent_left[:]
        
        for agent in agent_in_play:
            other_agent_names = ', '.join([a.name for a in agent_in_play if a is not agent])

            # if self.round == 0:
            instruction = f"""{self.rule.rule_explanation}\n
            You are {agent.name}. 
            You are bidding with { other_agent_names}.
            """
            # else:  
            #     instruction = f"""You are {agent.name}. 
            # You are bidding with { other_agent_names}."""
                 
            
            q_bid = QuestionYesNo(
                question_name = "q_bid",
                question_text = instruction+ f"""
            The transcript so far is: {self.transcript}.\n
            The current price is {self.current_price}. \n
            {self.rule.asking_prompt}""",
            )
            # print(instruction)
            # print(q_bid)
            # print(agent)
            # scenario = Scenario()
            # agent = Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds")
            survey = Survey(questions = [q_bid])
            result = survey.by(agent).by(self.model).run(cache = self.cache)
            response = result.select("q_bid").to_list()[0]
            
            print("=========",agent.name, response)

            if self.rule.ascend_descend == 'ascend':
                if response.lower() == 'no':
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
                    self.agent_left.remove(agent)
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
            elif self.rule.ascend_descend == 'descend':
                if response.lower() == 'yes':
                    self.agent_left.append(agent)
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
                else:
                    self.bid_list.append({"agent":agent.name,"bid": self.current_price, "decision": response.lower()})
            
        ## update the shared information
        self.transcript.append(self.share_information())
            
    def run(self):
        '''Run the clock until the ending condition'''
        stop_condition = False
        while stop_condition is False:
            self.bid_list = []
            self.run_one_round()
            print(self.round+1, '+++++done')
            self.round +=1
            stop_condition = self.declear_winner_and_price()
            print(self.__repr__())
            
        print(self.winner)
        return {'bidding history':self.bid_list, 'winner':self.winner}
    
    def share_information(self):
        if self.rule.open_blind == "open":
            return f'In round {self.round+1}, the decisions of the bidders are: {self.bid_list}'
        elif self.rule.open_blind == "blind":
            return None


    def declear_winner_and_price(self):
        ## The rules for deciding winners
        if self.rule.ascend_descend == "ascend":
            if len(self.agent_left) == 1:
                winner = self.agent_left[0].name
                price = self.current_price
                self.winner = {'winner':winner, 'price':price}
                return True
            elif len(self.agent_left) > 1:
                return False
            elif len(self.agent_left) == 0:
                print("No winner")
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
            

class Auction():
    '''
    This class manages the auction process using specified agents and rules.
    '''
    def __init__(self, number_agents, rule, cache=c, model='gpt-4o',temperature = 0):
        self.rule = rule        # Instance of Rule
        self.agents = []  # List of Agent instances
        self.number_agents = number_agents
        self.model= Model(model, temperature=temperature)
        self.cache = cache
        
        self.bids = []          # To store bid values
        self.history = []
        self.values_list = []
        
    def draw_value(self, common_range=(10, 100), private_range=20, seed=1234):
        '''
        Determine the values for each bidder using a common value and a private part.
        '''
        # make it reproducible
        random.seed(seed)
        
        # Generate a common value from a range
        if self.rule.private_value == 'private':
            common_value = 0
        elif self.rule.private_value == 'common':
            common_value = random.randint(*common_range)
        else: 
            raise ValueError(f"Rule {self.rule.private_value} not allowed")

        # Generate a private value for each agent and sum it with the common value
        for _ in range(self.number_agents):  # Now self.number_agents should be an integer
            private_part = random.randint(0, private_range)
            total_value = common_value + private_part
            self.values_list.append(total_value)
        print("The values for each bidder are:", self.values_list)

        
    def build_bidders(self):
        '''Instantiate bidders with the value and rule'''
        for i in range(self.number_agents): 
            # rule_prompt = self.rule.rule_explanation
            value_prompt = f"Your value towards to the money prize is {self.values_list[i]}"
            goal_prompt = "You need to maximize your profits. If you win the bid, your profit is your value for the prize subtracting by your final bid. If you don't win, your profit is 0."
            
            agent_traits = {
                "value": value_prompt,
                "goal": goal_prompt
            }
            agent = Agent(name=f"Bidder {i+1}", traits = agent_traits )
                        #   , instruction=rule_prompt)
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
        
        # store the history
        self.history=history
        
    def data_to_json(self, output_dir:str, timestring:str):
        save_json(self.history, f"result__{timestring}.json", output_dir)
        
    def run_repeated(self, times=1):
        i = 0
        while i < times:
            self.run()
            i+=1
        
            
        
if __name__ == "__main__":
    
    # agents = [
    #     Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds"),
    #     Agent(name = "Robin", instruction = "You are bidder 2, you need to stay for 3 round"),
    #     Agent(name = "Ben", instruction = "You are bidder 3"),
    # ]
    
    rule = Rule(seal_clock='seal', ascend_descend='ascend',price_order='second', private_value='common',open_blind='open')
    rule.describe()
    
    model_list = ["gpt-4-1106-preview", "gpt-4-turbo", "gpt-3.5","gpt-4o"]
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
    a = Auction(number_agents=3, rule=rule)
    a.draw_value(common_range=(10, 40), private_range=40,seed=1456)
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