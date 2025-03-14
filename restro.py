#!/usr/bin/env python3

import rospy
import actionlib
import threading
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from std_msgs.msg import String

# Define positions (Modify x, y, theta values as per your map)
POSITIONS = {
    "home": (0, 0, 0),
    "kitchen": (2, 0, 0),
    "table1": (2, 2, 0),
    "table2": (0, 2, 0),
    "table3": (0, 0, 2)
}

TIMEOUT = 10  # Time in seconds to wait for confirmation

class RestroRobot:
    def __init__(self):
        rospy.init_node('restro_robot', anonymous=True)
        
        # Action client for move_base
        self.client = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        self.client.wait_for_server()
        rospy.loginfo("Connected to move_base server.")

        # Robot states
        self.task_cancelled = False

    def send_goal(self, location):
        """ Sends the robot to the given location """
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = location[0]
        goal.target_pose.pose.position.y = location[1]
        goal.target_pose.pose.orientation.w = 1.0  # Fixed orientation

        self.client.send_goal(goal)
        self.client.wait_for_result()
        rospy.loginfo(f"Reached {location}")

    def wait_for_confirmation(self, message):
        """ Waits for user confirmation with a timeout """
        print(f"\n{message} (yes/cancel, auto-cancel in {TIMEOUT} sec): ")
        
        confirmation = [None]  # Use list for mutable reference
        def get_input():
            confirmation[0] = input().strip().lower()
        
        input_thread = threading.Thread(target=get_input)
        input_thread.start()
        input_thread.join(timeout=TIMEOUT)
        
        if confirmation[0] == "yes":
            print("Confirmation received!")
            return True
        else:
            print("No confirmation received or task cancelled.")
            return False

    def process_single_order(self, order):
        """ Processes a single order (list of tables to visit) """
        if not order:
            print("No valid tables in this order.")
            return
        
        print(f"Processing order: {order}")

        # Move to kitchen
        self.send_goal(POSITIONS["kitchen"])
        if not self.wait_for_confirmation("Please confirm if the robot has reached the kitchen"):
            print("No confirmation at kitchen. Returning home.")
            self.send_goal(POSITIONS["home"])
            return
        
        # Move to tables
        for table in order:
            if self.task_cancelled:
                print("Task cancelled. Returning home.")
                self.send_goal(POSITIONS["home"])
                return

            self.send_goal(POSITIONS[table])
            if not self.wait_for_confirmation(f"Please confirm if the food has been delivered to {table}"):
                print(f"No confirmation at {table}, skipping to next.")
                continue
            

        print("Order completed. Returning kitchen,then home.")
        self.send_goal(POSITIONS["kitchen"])
        self.send_goal(POSITIONS["home"])

    def process_orders(self):
        """ Main function to process multiple orders """
        while not self.task_cancelled:
            print("\nPlease enter the order (comma-separated table names like 'table1, table2'):")
            order_input = input().strip()

            # Parse the order input and split into tables
            order = [table.strip() for table in order_input.split(',') if table.strip() in POSITIONS]

            if not order:
                print("Invalid order. Please enter valid table names.")
                continue

            self.process_single_order(order)

            # Ask the user if they want to place another order
            print("\nWould you like to place another order? (yes/no)")
            user_input = input().strip().lower()
            if user_input != 'yes':
                print("Ending the task.")
                break

if __name__ == '__main__':
    try:
        robot = RestroRobot()
        robot.process_orders()
    except rospy.ROSInterruptException:
        print("Navigation interrupted.")
