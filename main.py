from edsl.data import Cache
import logging
import os
import pandas as pd
import sys

from util import Rule, Auction

## output files
timestring = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")

    
if __name__ == "__main__":
    c = Cache()
    
    #Rule Option Menu for Anand
    # seal_clock= 'seal' or 'clock' 
    # ascend_descend='ascend' or 'descend' if seal_clock= 'clock' 
    # price_order='first' or 'second' or 'third' if seal_clock= 'seal'
    # private_value='private' or 'common'
    # open_blind='open' or 'blind' if seal_clock= 'clock' 
            #i.e. bidder don't see the drop out in the clock
    seal_clock='clock'
    ascend_descend='ascend'
    price_order='second'
    private_value='common'
    open_blind='open'
    
    ## Set the output file
    output_dir = f"experiment_logs/{seal_clock}_{ascend_descend}_{price_order}_{private_value}_{open_blind}"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    ## Set the rule
    rule = Rule(seal_clock=seal_clock, ascend_descend=ascend_descend, price_order=price_order, private_value=private_value,open_blind=open_blind, rounds=2, common_range=[10, 10], private_range=10, increment=3)
    rule.describe()

    ## Instantiate the auction
    a = Auction(number_agents=3, rule=rule, output_dir=output_dir, timestring=timestring, cache=c, model ='gpt-4o', temperature=0)
    a.draw_value(seed=1235)
    ## Agent build
    # a.build_bidders()
    # a.run()
    a.run_repeated()
    
    # ## store the analysis data
    # a.data_to_json(output_dir=output_dir, timestring=timestring)
    ## store the raw data
    c.write_jsonl(os.path.join(output_dir,f"raw_output__{timestring}.jsonl"))