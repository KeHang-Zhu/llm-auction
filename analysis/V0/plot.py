import numpy as np
import matplotlib.pyplot as plt

# Calculating the average of each list
list_2p_1 = [4.333333333333333, 1.6666666666666667, 1.6666666666666667, 2.3333333333333335, 2.3333333333333335, 2.0, 3.6666666666666665, 3.3333333333333335, 3.3333333333333335, 2.6666666666666665]
list_2p_2 =[3.6666666666666665, 2.6666666666666665, 0.3333333333333333, 4.666666666666667, 6.333333333333333, 1.0, 5.0, 5.666666666666667, 4.333333333333333, 2.6666666666666665]
list_2p_3 =[4.0, 2.0, 3.3333333333333335, 2.3333333333333335, 2.3333333333333335, 1.6666666666666667, 0.6666666666666666, 0.6666666666666666, 2.6666666666666665, 3.6666666666666665]
list_2p_4 =[4.0, 4.666666666666667, 3.0, 3.3333333333333335, 1.3333333333333333, 1.6666666666666667, 2.6666666666666665, 2.0, 1.6666666666666667, 6.333333333333333]
list_2p_5 = [2.3333333333333335, 5.0, 2.0, 4.0, 1.6666666666666667, 4.0, 3.3333333333333335, 2.3333333333333335, 2.3333333333333335, 2.0]
# mad_2p_1 = np.mean([list_2p_1, list_2p_2, list_2p_3, list_2p_4, list_2p_5], axis=0)

list_2p_6= [2.0, 1.3333333333333333, 1.6666666666666667, 1.6666666666666667, 1.6666666666666667, 1.3333333333333333, 2.0, 2.3333333333333335, 2.0, 2.0]
list_2p_7 = [2.6666666666666665, 2.0, 0.3333333333333333, 3.6666666666666665, 5.333333333333333, 1.0, 4.333333333333333, 5.666666666666667, 4.666666666666667, 2.0]
list_2p_8 = [1.0, 5.333333333333333, 3.0, 4.0, 2.0, 2.0, 1.6666666666666667, 1.6666666666666667, 1.6666666666666667, 6.333333333333333]
list_2p_9 = [2.0, 3.0, 2.0, 3.0, 1.3333333333333333, 3.6666666666666665, 3.3333333333333335, 1.6666666666666667, 1.6666666666666667, 2.0]
list_2p_10 = [2.3333333333333335, 3.3333333333333335, 6.333333333333333, 1.6666666666666667, 1.6666666666666667, 4.666666666666667, 2.6666666666666665, 4.666666666666667, 1.6666666666666667, 4.0]

data_2p = np.array([list_2p_1, list_2p_2, list_2p_3, list_2p_4, list_2p_5, list_2p_6, list_2p_7, list_2p_8, list_2p_9, list_2p_10])
mad_2p = np.mean(data_2p, axis=0)
std_2p = np.std(data_2p, axis=0)

# mad_2p_2 =[2.        , 3.        , 2.66666667, 2.8       , 2.4       ,
#        2.53333333, 2.8       , 3.2       , 2.33333333, 3.26666667]

# mad_2p  =  np.mean([mad_2p_1, mad_2p_2], axis=0)

list1 = [0.0, 3.5, 5.0, 1.0, 1.0, 3.0, 0.5, 2.5, 2.5, 2.0]
list2 = [2.0, 2.5, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0, 2.0, 1.5]
list3 = [2.0, 2.0, 1.5, 0.3333333333333333, 3.5, 0.5, 0.5, 3.0, 1.5, 2.0]
list4 = [1.5, 1.0, 2.0, 1.0, 3.0, 2.0, 4.5, 2.3333333333333335, 0.5, 1.5]
list5 = [0.5, 2.5, 2.0, 0.5, 1.3333333333333333, 1.0, 1.0, 2.0, 0.5, 0.0]
data_acb = [list1, list2, list3, list4, list5]
mad_acb = np.mean(data_acb, axis=0)
std_acb = np.std(data_acb, axis=0)


mad_ac_1 = [1.0, 0.5, 0.0, 0.5, 0.0, 0.5, 1.0, 0.0, 0.0, 0.5]
mad_ac_2 = [0.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.0, 0.5, 0.5]
data_ac = [mad_ac_1, mad_ac_2]
mad_ac = np.mean(data_ac, axis=0)
std_ac = np.std(data_ac, axis=0)

# Creating the plot
plt.figure(figsize=(10, 5))

rounds = np.arange(1, 11)

# Offset for shifting plots
offset = 0.1

plt.errorbar(rounds - offset, mad_2p, yerr=std_2p, fmt='o', linestyle='-', color='blue', elinewidth=2, capsize=3, alpha=0.2, label='SPSB')
plt.errorbar(rounds, mad_acb, yerr=std_acb, fmt='o', linestyle='--', color='red', elinewidth=2, capsize=3, alpha=0.2, label='AC-B')
plt.errorbar(rounds + offset, mad_ac, yerr=std_ac, fmt='o', linestyle='-.', color='green', elinewidth=2, capsize=3, alpha=0.2, label='AC')

# Annotating the end of each line with the label
plt.annotate('SPSB', (rounds[-1]+1, round(mad_2p[-1])+0.5), color='blue', fontsize=15,
             xytext=(10, 0), textcoords="offset points", ha='right')
plt.annotate('AC-B', (rounds[-1]+1, round(mad_acb[-1])+0.5), color='red', fontsize=15,
             xytext=(10, 0), textcoords="offset points", ha='right')
plt.annotate('AC', (rounds[-1]+0.8 , round(mad_ac[-1])+0.5), color='green', fontsize=15,
             xytext=(10, 0), textcoords="offset points", ha='right')


# Plotting lines with higher opacity
plt.plot(rounds - offset, mad_2p, 'o-', color='blue', label='SPSB Line', alpha=0.8)
plt.plot(rounds, mad_acb, 'o--', color='red', label='AC-B Line', alpha=0.8)
plt.plot(rounds + offset, mad_ac, 'o-.', color='green', label='AC Line', alpha=0.8)


# Plotting solid markers separately with full opacity
plt.scatter(rounds - offset, mad_2p, color='blue', s=40, edgecolors='black', label='SPSB Dots', alpha=1)
plt.scatter(rounds, mad_acb, color='red', s=40, edgecolors='black', label='AC-B Dots', alpha=1)
plt.scatter(rounds + offset, mad_ac, color='green', s=40, edgecolors='black', label='AC Dots', alpha=1)



# plt.plot(rounds, mad_2p, marker='o', linestyle='-', color='blue', label='2P')
# plt.plot(rounds, mad_ac, marker='.', linestyle='--', color='red', label='AC')
# plt.plot(rounds, mad_acb, marker='', linestyle='-.', color='green', label='AC-B')

plt.xlabel('Round', fontsize=13)
plt.ylabel('Average |Bid - Value|', fontsize=13)
plt.xticks(fontsize=13)
plt.yticks(fontsize=13)
plt.title('Obviously Strategy-proof Auctions', fontsize=15)
# plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
plt.ylim([-0.1,4.5])
plt.xlim([0.5, 11.7])

# Showing the plot
plt.grid(True)
# plt.show()
plt.savefig("OSP.png")
