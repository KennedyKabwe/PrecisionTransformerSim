import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.plot(x, y)
plt.title("Test Plot")
plt.xlabel("x")
plt.ylabel("sin(x)")
plt.grid(True)

plt.show()