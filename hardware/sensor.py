from gpiozero import DistanceSensor
import time

class UltrasonicScanner:
    def __init__(self, trigger_pin, echo_pin, threshold_cm=15.0):
        # gpiozero works with meters, so we convert cm to meters
        self.threshold_m = threshold_cm / 100.0
        
        # max_distance=1.0 makes the sensor respond faster by ignoring objects further than 1 meter
        self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=1.0)
        
        print(f"[Hardware] Scanner ready. Trigger: {trigger_pin}, Echo: {echo_pin}, Threshold: {threshold_cm}cm")

    def get_raw_distance_cm(self):
        # Convert the raw distance from meters to centimeters and round it
        return round(self.sensor.distance * 100, 1)

    def is_item_present(self):
        """
        Checks if an object is within the threshold distance.
        Uses a simple debouncing algorithm to filter out sensor noise.
        """
        valid_reads = 0
        samples = 3
        
        for _ in range(samples):
            # Check if the current distance is less than our threshold
            if self.sensor.distance < self.threshold_m:
                valid_reads += 1
            
            # Wait 50 milliseconds before the next check
            time.sleep(0.05)
            
        # Return True only if at least 2 out of 3 readings confirmed the object
        return valid_reads >= 2
