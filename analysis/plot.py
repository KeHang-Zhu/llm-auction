import numpy as np
import matplotlib.pyplot as plt

# Calculating the average of each list
# list_2p_1 = [4.333333333333333, 1.6666666666666667, 1.6666666666666667, 2.3333333333333335, 2.3333333333333335, 2.0, 3.6666666666666665, 3.3333333333333335, 3.3333333333333335, 2.6666666666666665]
# list_2p_2 =[3.6666666666666665, 2.6666666666666665, 0.3333333333333333, 4.666666666666667, 6.333333333333333, 1.0, 5.0, 5.666666666666667, 4.333333333333333, 2.6666666666666665]
# list_2p_3 =[4.0, 2.0, 3.3333333333333335, 2.3333333333333335, 2.3333333333333335, 1.6666666666666667, 0.6666666666666666, 0.6666666666666666, 2.6666666666666665, 3.6666666666666665]
# list_2p_4 =[4.0, 4.666666666666667, 3.0, 3.3333333333333335, 1.3333333333333333, 1.6666666666666667, 2.6666666666666665, 2.0, 1.6666666666666667, 6.333333333333333]
# list_2p_5 = [2.3333333333333335, 5.0, 2.0, 4.0, 1.6666666666666667, 4.0, 3.3333333333333335, 2.3333333333333335, 2.3333333333333335, 2.0]
# mad_2p_1 = np.mean([list_2p_1, list_2p_2, list_2p_3, list_2p_4, list_2p_5], axis=0)

mad_2p =[2.        , 3.        , 2.66666667, 2.8       , 2.4       ,
       2.53333333, 2.8       , 3.2       , 2.33333333, 3.26666667]

# mad_2p  =  np.mean([mad_2p_1, mad_2p_2], axis=0)

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