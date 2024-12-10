from edsl.data import Cache
import logging
import os
import pandas as pd
import sys
from util import Rule, Auction
from util_human import Auction_human
from util_plan import Auction_plan, Rule_plan
import concurrent.futures

def run_auction(i, human, number_agents, rule, output_dir, c):
    timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    if human:
        a = Auction_human(number_agents=number_agents, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model='gpt-4o', temperature=1)
    else:
        a = Auction(number_agents=number_agents, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model='gpt-4o', temperature=1)
    a.draw_value(seed=1299 + i)
    a.run_repeated()
    c.write_jsonl(os.path.join(output_dir, f"raw_output__{timestring}.jsonl"))

if __name__ == "__main__":
    c = Cache()
    
    # Rule Option Menu
    seal_clock = 'seal'
    ascend_descend = ''
    price_order = 'second'
    private_value = 'private'
    open_blind = 'close'
    number_agents = 3
    human = False
    
    output_dir = f"experiment_logs/V5/{seal_clock}_{ascend_descend}_{price_order}_{private_value}_{open_blind}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    rule = Rule(seal_clock=seal_clock, price_order=price_order, private_value=private_value, open_blind=open_blind, rounds=15, common_range=[0, 79], private_range=99, increment=1, number_agents=number_agents)
    rule.describe()

    N = 5 # Repeat for N times
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_auction, i, human, number_agents, rule, output_dir, c) for i in range(N)]

    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()
        except Exception as e:
            print(f"An error occurred: {e}")
