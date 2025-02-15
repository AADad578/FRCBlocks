# FRCBlocks
 
Requirements:
    pip install pygame 
    pip install anytree

Project Description: 
    This project is made to provide students with a GUI interface for creating an autonomous program for an FRC 2024 robot.
    This is meant to function as a Hour of Code style program that provides users with a grid based robot that they can
    move around using drag and drop block code. At the culmination of the event the students can then run the block code 
    they created on a real robot.

How To Use:
    Create a challenging setup for the students. See simSetup.txt
    Once you run the program a resizable window will appear which can be interacted with.
    On the left there are the blocks that can be used.
    The middle area is the code, drag blocks from the left to the center for use.
    The right area is the simulation field.
    The top contains various functions that will be useful.
    The checkmark icon validates the code and ensures that there aren't any open loops or extra close loop blocks
    The play icon runs the simulation
    The reset icon resets the simulation to the inital state
    The java icon generates java code and saves it into the javaIn.java file at the comment given. This can be changed to 
    any file, but you must maintain the comment where you want the code to go.
    
    To intake a note, the robot must have intake on (green dot) and move into the note from any direction.
    When shooting a note, it will travel in the direction of the arrow.

    Parallel Groups should not move or turn in multiple directions at the same point; may cause issues in sim, 
    will cause issues on a real robot
    
    There are three different scrollable areas; Scroll wheel will scroll whichever you are hovering mouse over.
    Dragging any area that doesn't have a block will move the area.
    
Code Description:
    See flowcharts in Flowcharts.pdf
    
    Most visible classes inherit from a visual class and a functional class
    Functional classes (eventually) inherit from the Object class which inherits pygame's surface
    Code blocks have a runSim function which dictate what happens when they are used in simulation
    Generator blocks create a copy of the real code block each time they are clicked
    
Author: 
    Ankur Raghavan, Team 2869

Version:
    1.1 (2/15/2025)