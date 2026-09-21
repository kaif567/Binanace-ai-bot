import math

n = 99
p = 44 / 99

# Normal approximation for 95% CI (Z = 1.96)
z = 1.96
se = math.sqrt((p * (1 - p)) / n)
lower = p - z * se
upper = p + z * se

print(f"Observed Accuracy: {p*100:.1f}% (44/99)")
print(f"95% Confidence Interval: [{lower*100:.1f}% to {upper*100:.1f}%]")

# Simple Monte Carlo for P-value (how likely is 44 or worse if it's a 50/50 coin flip?)
import random
random.seed(42)
trials = 100000
worse_or_equal = 0
for _ in range(trials):
    heads = sum(1 for _ in range(n) if random.random() < 0.5)
    if heads <= 44:
        worse_or_equal += 1

print(f"Probability this is just an unlucky 50/50 coin flip: {(worse_or_equal/trials)*100:.1f}%")
