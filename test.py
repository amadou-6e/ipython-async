%%asyncpython
import time
import math

print("Starting comprehensive asynchronous Python test...")
print("Performing calculations:")

# Loop to simulate iterative processing and calculations.
for i in range(1, 6):
    time.sleep(1)  # Simulate work with a delay.
    result = math.sqrt(i * 10)
    print(f"Iteration {i}: sqrt({i*10}) = {result}")

print("\nNow testing error handling:")
try:
    print("About to perform a division by zero...")
    _ = 10 / 0  # Intentional error.
except Exception as e:
    print(f"Expected error caught: {e}")

print("\nResuming normal execution:")
# Additional loop to continue after the error.
for j in range(6, 9):
    time.sleep(1)
    print(f"Iteration {j}: continuing after error...")

print("\nAsynchronous Python test completed successfully!")
