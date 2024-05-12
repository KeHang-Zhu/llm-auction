from textwrap import dedent
from itertools import cycle
import random
import os

from edsl import Agent, Scenario, Survey
from edsl.data import Cache
from edsl.Base import Base
from edsl.questions import QuestionFreeText, QuestionYesNo
from edsl.prompts import Prompt
from edsl.questions import QuestionMultipleChoice

class payoff():
    def __init__(self):
        self.current_bid = []
        self.payoff= []
    
class Game():
    def __init__(self, agents, payoff, history=None):
        
        ## for setting up stage
        self.payoff = payoff
        self.agents = agents
        ## For repeated game:
        self.history = history

        self.choice_list = []   
        self.transcript = [] 
    
    def __repr__(self):
        return f'Clock Auction: (bid_list={self.choice_list})'
        
    def calculate_payoff(self):
        pass
    
    def play_one_round(self):
        '''run for one round'''
        ## calculate the next clock price
        self.calculate_payoff()
        
        ## update the shared information
        self.transcript.append(self.share_information())

        for agent in self.agents:
            other_agent_names = ', '.join([a.name for a in self.agents if a is not agent])
            
            q_game = QuestionMultipleChoice(
                question_name = "q_game",
                question_text = dedent("""\
            You are {{ agent_name }}. 
            You are bidding with {{ other_agent_names}}.
            The transcript so far is: 
            {{ transcript }}
            It is your turn to choose your action.
            Do you want to stay or drop out at the current price {{current_price}}
            """), 
            )
            scenario = Scenario({
                "agent_name": agent.name, 
                "other_agent_names": other_agent_names, 
                "transcript": self.transcript},
                                )
            
            survey = Survey(questions = [q_game])
            result = survey.by(scenario).by(agent).run()
            response = result.select("q_game").to_list()[0]
            self.choice_list.append({"name":agent.name, "choice": response})

        self.calculate_payoff()
                
            
    def play(self, rounds=10):
        '''Run the clock until the ending condition'''
        i = 0
        while i < rounds:
            self.play_one_round()
            print(self.__repr__())
            i+=1
            
        


if __name__ == "__main__":
    
    agents = [
        Agent(name = "John", instruction = "You are bidder 1, you need to stay for 2 rounds"),
        Agent(name = "Robin", instruction = "You are bidder 2, you need to stay for 3 round"),
        Agent(name = "Ben", instruction = "You are bidder 3"),
    ]
    
    
    model = "gpt-4-turbo"
    q = QuestionFreeText(question_text = dedent("""\
        What's your goal?
        """), 
        question_name = "response"
    )
    survey = Survey([q])
    
    transcript = []
    s = Scenario({'agent_1_name': agents[0].name, 
                  'agent_2_name': agents[1].name, 
                  'transcript': transcript}) 
    results = survey.by(agents[1]).by(s).run(cache = c)
    print(results)
    response = results.select('response').first()
    print("====", response )
    
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
    a.draw_value()
    ## Test Agent build
    a.build_bidders()
    print(a.agents)
    
    ## Test on running
    a.run()
    
    ## Test on the descend clock
    # How to design the asking prompt
    
    ## Test for repeated game
    
    ## Test for Scenario
    # what kind of infor to put into the scenatrio
    
    # auction = Auction(agents, rule=rule)