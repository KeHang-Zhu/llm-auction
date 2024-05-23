import numpy as np
import matplotlib.pyplot as plt

# Calculating the average of each list
mad_2p  =[2.        , 3.        , 2.66666667, 2.8       , 2.4       ,
       2.53333333, 2.8       , 3.2       , 2.33333333, 3.26666667]

list1 = [0.0, 3.5, 5.0, 1.0, 1.0, 3.0, 0.5, 2.5, 2.5, 2.0]
list2 = [2.0, 2.5, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0, 2.0, 1.5]
list3 = [2.0, 2.0, 1.5, 0.3333333333333333, 3.5, 0.5, 0.5, 3.0, 1.5, 2.0]
list4 = [1.5, 1.0, 2.0, 1.0, 3.0, 2.0, 4.5, 2.3333333333333335, 0.5, 1.5]
list5 = [0.5, 2.5, 2.0, 0.5, 1.3333333333333333, 1.0, 1.0, 2.0, 0.5, 0.0]

# Calculating the mean of the combined lists
mad_acb = np.mean([list1, list2, list3, list4, list5], axis=0)


mad_ac = [1.0, 0.5, 0.0, 0.5, 0.0, 0.5, 1.0, 0.0, 0.0, 0.5]
rounds = range(1,11)

plt.plot(rounds, mad_2p, marker='o', linestyle='-', color='blue', label='2P')
plt.plot(rounds, mad_ac, marker='.', linestyle='--', color='red', label='AC')
plt.plot(rounds, mad_acb, marker='', linestyle='-.', color='green', label='AC-B')
plt.xlabel('Round')
plt.ylabel('Mean Absolute Deviation of Bids from Values')
# plt.title('Mean Absolute Deviation of Bids from Values vs Round')
plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.grid(True)

plt.show()