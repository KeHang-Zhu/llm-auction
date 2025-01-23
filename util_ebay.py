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

from dataclasses import dataclass
from typing import List, Optional

## -  make a timeframe data class to store everybody’s reactions

status = ["PENDING", "BID", "WITHDRAW", "NONE"]  # Possible actions

## in each time frame, the player can choose to 

@dataclass
class AuctionStatus:
    """
    Stores the state of the auction in one time period.
    """
    period_id: int                # Current time step (0, 1, 2, ...)
    is_finished: bool             # Has the auction ended at this time step?
    current_price: int            # The eBay 'current' winning price after proxy logic
    reserve_price: int            # Keep track for info
    actions: dict                 # Player actions for this period (e.g., {"player1":"BID", "player2":"NONE", ...})
    max_bids: dict                # Player max-bids after this period (e.g., {"player1":100, "player2":120, ...})
    highest_bidder: Optional[str] # Track who is currently winning


def save_json(data, filename, directory="."):
    """
    Saves data to a JSON file in the specified directory.
    """
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    return file_path


class Ebay:
    def __init__(
        self,
        agents: List[str],
        start_price: int,
        reserve_price: int,
        bid_increment: int,
        private_values: dict,
        total_periods: int = 5
    ):
        """
        :param agents: List of agent names/IDs, e.g. ["player1", "player2", ...]
        :param start_price: Starting price for the auction
        :param reserve_price: Hidden reserve price. Auction is valid only if final >= reserve_price
        :param bid_increment: Minimum increment for outbidding
        :param private_values: dict of each agent's private value, e.g. {"player1":120, "player2":100}
        :param total_periods: How many time steps the auction will run
        """
        self.agents = agents
        self.start_price = start_price
        self.reserve_price = reserve_price
        self.bid_increment = bid_increment
        self.private_values = private_values
        
        # eBay state
        self.current_price = start_price
        self.highest_bidder = None
        
        # We track each player's maximum willingness to pay (only known to that player!)
        # For simulation, we'll track them in code. Realistically, players don't reveal these to each other.
        # We start with them as None or 0:
        self.current_max_bids = {agent: 0 for agent in agents}
        
        # Auction log
        self.time_history: List[AuctionStatus] = []
        
        # Auction length in discrete steps
        self.total_periods = total_periods
        
        # Flag to indicate if auction is finished
        self.auction_finished = False

    def run(self):
        """
        Main driver: runs the auction for `self.total_periods` steps (or until ended).
        """
        for t in range(self.total_periods):
            if self.auction_finished:
                break
            
            # Gather actions from each agent (BID, WITHDRAW, or do nothing).
            actions_in_this_period = {}
            for agent in self.agents:
                actions_in_this_period[agent] = self._get_agent_action(agent, t)

            # Update the highest bidder, current price based on proxy bidding
            self._process_actions(actions_in_this_period)
            
            # Create a snapshot of the current state
            status_snapshot = AuctionStatus(
                period_id=t,
                is_finished=self.auction_finished,
                current_price=self.current_price,
                reserve_price=self.reserve_price,
                actions=actions_in_this_period.copy(),
                max_bids=self.current_max_bids.copy(),
                highest_bidder=self.highest_bidder
            )
            self.time_history.append(status_snapshot)
            
        
        # After loop ends or last period is done, finalize the outcome
        self._finalize_auction()

    def _get_agent_action(self, agent: str, current_period: int) -> str:
        """
        Decide the agent's action for this time step.
        
        Returns one of:
         - "BID": choose a new max
         - "WITHDRAW": remove from bidding
         - "NONE": do nothing
        """

        general_prompt_str = Prompt.from_txt("Prompt/ebay_asking.txt")
        general_prompt = general_prompt_str.render({"period": current_period})

        q_action = QuestionFreeText(
            question_name = "q_action",
            question_text = general_prompt,
        )
        survey = Survey(questions = [q_action])
        result = survey.by(self.model).run(cache = self.cache)
        response = result.select("q_action").to_list()[0]

        ## Parse the result
        action = self.parse_decision(response)
        
        return action

    def _process_actions(self, actions: dict):
        """
        Updates the eBay proxy bidding state given all players' declared actions.
        """
        # For each agent who says "BID", we update their maximum.
        # Then recalculate the current price based on the top 2 maximums.
        
        # 1) Update maximum bids for each agent who chooses to BID.
        for agent, act in actions.items():
            if act == "BID":
                # Suppose the agent chooses a new maximum that is
                #  (agent's private_value) in a naive approach:
                self.current_max_bids[agent] = self.private_values[agent]
            elif act == "WITHDRAW":
                # In many eBay contexts, you can't fully withdraw your earlier bid,
                # but for demonstration, let's set max to 0 (i.e., not competing).
                self.current_max_bids[agent] = 0
            else:
                # "NONE" means do nothing, keep prior maximum
                pass

        # 2) Determine the highest and second-highest bids
        sorted_bids = sorted(self.current_max_bids.items(), key=lambda x: x[1], reverse=True)
        
        # If no one has a positive bid, no winner for now
        if len(sorted_bids) == 0 or sorted_bids[0][1] <= 0:
            self.highest_bidder = None
            self.current_price = self.start_price  # or keep it at old self.current_price
            return
        
        top_bidder, top_bid = sorted_bids[0]
        if len(sorted_bids) > 1:
            second_bidder, second_bid = sorted_bids[1]
        else:
            second_bid = 0
        
        # 3) Proxy bidding logic to set the *current price*:
        # eBay sets the current price to either second-highest + increment or top_bid (if second is close).
        if second_bid > 0:
            new_price = min(top_bid, second_bid + self.bid_increment)
        else:
            # If there's no second highest, the price starts at the start_price or goes up by increment
            # but realistically eBay sets the price to the starting price (if first bidder) or
            # second_highest + increment. We'll do a simple approach:
            new_price = max(self.current_price, self.start_price)  # or just the start_price if first bid
            if new_price < top_bid:
                # if the top_bid is above the start price, we can set the price to start_price
                new_price = self.start_price
        
        self.highest_bidder = top_bidder
        self.current_price = new_price

    def _finalize_auction(self):
        """
        Resolve the final winner and price. Check reserve, etc.
        """
        # Check if final price >= reserve. If not, no sale.
        winner = self.highest_bidder
        final_price = self.current_price
        
        if winner is None or final_price < self.reserve_price:
            print(f"No winner. Reserve not met or no valid bids. Final price: ${final_price}")
        else:
            print(f"Auction complete. Winner: {winner} at ${final_price}")

        # Mark auction as finished
        self.auction_finished = True

        # Optionally, save the entire history to JSON
        data_to_save = [vars(snap) for snap in self.time_history]
        save_json(data_to_save, filename="auction_history.json", directory=".")
        
        return
        

    def parse_decision(self, action_txt):
        ## parse the decision
        ...
        action= ...
        return action


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

        
    def __repr__(self):
        return repr(self.agent)

    def build_bidder(self, current_round):

        self.agent = Agent(name=self.name)
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

        save_json(self.data_to_save, f"result_{self.round_number}_{self.timestring}.json", self.output_dir)
        
    def run_repeated(self):
        self.build_bidders()
        while self.round_number < self.rule.round:
            self.run()
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




