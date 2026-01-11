import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker



fig, axs = plt.subplots(2, 2, figsize=(12, 7))
plt.subplots_adjust(hspace=0.5, wspace=0.5)

#Figure 1 (0, 0):

cats00 = ["Strongly\ndisagree", "Disagree", "Neutral", "Agree", "Strongly\nagree"]
vals00 = [0, 0, 5, 9, 3]

axs[0,0].bar(cats00, vals00, edgecolor="#4A4A4A", color=["#f9a73e", "#f5be7c", "gray", "#4E6592", "#315396"])

axs[0,0].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

axs[0,0].set_xlabel("Response category", labelpad=3)
axs[0,0].set_ylabel("# responses", labelpad=3)
axs[0,0].set_title("The webapp could help me improve my ability to read code")

ttl00 = axs[0,0].title
ttl00.set_weight("bold")

xlab00 = axs[0,0].xaxis.get_label()
ylab00 = axs[0,0].yaxis.get_label()

xlab00.set_style('italic')
xlab00.set_size(10)
ylab00.set_style('italic')
ylab00.set_size(10)

axs[0,0].spines['right'].set_color((.8, .8, .8))
axs[0,0].spines['top'].set_color((.8, .8, .8))
axs[0,0].spines['left'].set_color((.8, .8, .8))


#Figure 2 (0, 1):

cats01 = ["Strongly\ndisagree", "Disagree", "Neutral", "Agree", "Strongly\nagree"]
vals01 = [0, 3, 3, 8, 3]

axs[0,1].bar(cats01, vals01, edgecolor="#4A4A4A", color=["#f9a73e", "#f5be7c", "gray", "#4E6592", "#315396"])

axs[0,1].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

axs[0,1].set_xlabel("Response category", labelpad=3)
axs[0,1].set_ylabel("# responses", labelpad=3)
axs[0,1].set_title("I would enjoy using this webapp as part of a CS course")

ttl01 = axs[0,1].title
ttl01.set_weight("bold")

xlab01 = axs[0,1].xaxis.get_label()
ylab01 = axs[0,1].yaxis.get_label()

xlab01.set_style('italic')
xlab01.set_size(10)
ylab01.set_style('italic')
ylab01.set_size(10)

axs[0,1].spines['right'].set_color((.8, .8, .8))
axs[0,1].spines['top'].set_color((.8, .8, .8))
axs[0,1].spines['left'].set_color((.8, .8, .8))

#Figure 3 (1, 0): 

cats10 = ["Strongly\ndisagree", "Disagree", "Neutral", "Agree", "Strongly\nagree"]
vals10 = [0, 2, 5, 8, 2]

axs[1,0].bar(cats10, vals10, edgecolor="#4A4A4A", color=["#f9a73e", "#f5be7c", "gray", "#4E6592", "#315396"])

axs[1,0].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

axs[1,0].set_xlabel("Response category", labelpad=3)
axs[1,0].set_ylabel("# responses", labelpad=3)
axs[1,0].set_title("There was enough problem variety")

ttl10 = axs[1,0].title
ttl10.set_weight("bold")

xlab10 = axs[1,0].xaxis.get_label()
ylab10 = axs[1,0].yaxis.get_label()

xlab10.set_style('italic')
xlab10.set_size(10)
ylab10.set_style('italic')
ylab10.set_size(10)

axs[1,0].spines['right'].set_color((.8, .8, .8))
axs[1,0].spines['top'].set_color((.8, .8, .8))
axs[1,0].spines['left'].set_color((.8, .8, .8))

#Figure 4 (1, 1):

cats11 = ["Strongly\ndisagree", "Disagree", "Neutral", "Agree", "Strongly\nagree"]
vals11 = [0, 0, 2, 12, 3]

axs[1,1].bar(cats10, vals10, edgecolor="#4A4A4A", color=["#f9a73e", "#f5be7c", "gray", "#4E6592", "#315396"])

axs[1,1].yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

axs[1,1].set_xlabel("Response category", labelpad=3)
axs[1,1].set_ylabel("# responses", labelpad=3)
axs[1,1].set_title("The generated code was human like")

ttl10 = axs[1,1].title
ttl10.set_weight("bold")

xlab11 = axs[1,1].xaxis.get_label()
ylab11 = axs[1,1].yaxis.get_label()

xlab11.set_style('italic')
xlab11.set_size(10)
ylab11.set_style('italic')
ylab11.set_size(10)

axs[1,1].spines['right'].set_color((.8, .8, .8))
axs[1,1].spines['top'].set_color((.8, .8, .8))
axs[1,1].spines['left'].set_color((.8, .8, .8))

plt.show()