"""
Requirements:
    pip install pygame 
    pip install anytree

Project Description: 
    This project is made to provide students with a GUI interface for creating an autonomous program for an FRC 2024 robot.
    This is meant to function as a Hour of Code style program that provides users with a grid based robot that they can
    move around using drag and drop block code. At the culmination of the event the students can then run the block code 
    they created on a real robot.

How To Use:
    Create a challenging setup for the students. An example is located in simSetup.txt.
    Once you run the program, it will prompt you for this setup (leave blank for example)
    After that a resizable window will appear which can be interacted with.
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
"""

import math
import sys, pygame
import time
from anytree import NodeMixin, RenderTree

pygame.init()
size = width, height = 1500, 900
font = pygame.font.Font("freesansbold.ttf", 32)


# ---------
# GENERICS
class Object(
    pygame.Surface
):  # Generic Object, It has a size, position, and a collide function
    def __init__(self, size=(100, 100), pose=(500, 500)):
        self.item = 1
        pygame.Surface.__init__(self, size)
        self.fill(white)
        self.rect = self.get_rect()
        self.rect.x = pose[0]
        self.rect.y = pose[1]

    def collide(self, event):
        return self.rect.collidepoint(event.pos)


class TreeNode(NodeMixin):  # TreeNode, Can have a parent and children.
    # extends NodeMixin which helps with printing and general tree nodes
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.parent = None
        self.otherChild = None
        self.numChild = 1
        self.children = []
        self.isParallel = False
        self.hasRun = False

    def checkIfParallel(self):
        # figures out if a object is within a parallel group
        if self.parent:
            if (
                self.parent.numChild == 2
            ):  # if it's parent can have two children, the parent is a parallel group
                self.isParallel = True
            elif (
                self.parent.numChild == 1
            ):  # if it's parent has one child, it is in a parallel group if it's parent is in a parallel group
                self.isParallel = self.parent.isParallel
        else:  # if has no parent, can't be within parallel group
            self.isParallel = False
        return self.isParallel

    def findParents(self):
        # finds the parent node of this object
        # the parent is the closest node vertically above the object
        # if the parent is parallel, the center of the object must be within the parent block (x-axis only)
        parent = None
        amountAbove = math.inf
        for i in dragItems:
            if (
                not i.isParallel
                or self.rect.centerx < i.rect.right + blockSize
                and self.rect.centerx > i.rect.left - blockSize
            ):
                above = self.rect.y - i.rect.y
                if above > 0 and above < amountAbove:
                    parent = i
                    amountAbove = above
        self.parent = parent
        # add self to the parent's children if not already there
        if not self in self.parent.children:
            self.parent.children += (self,)
        # if parent is an endparallel, find the parallel above it and add self to the other child of that parallel group
        if str(self.parent) == "EndParallelGroup":
            item = self.parent
            while item != None:
                if str(item) == "ParallelGroup":
                    item.otherChild = self
                    break
                item = item.parent
        # if parent is an endloop, find the loop above it and add self to the other child of that loop group
        elif str(self.parent) == "EndLoop":
            item = self.parent
            while item != None:
                if str(item) == "Loop":
                    item.otherChild = self
                    break
                item = item.parent

    def command(self):
        # Returns the command for this object, used to generate java code
        match len(self.children):
            case 0:  # if no children
                return f"new {str(self)}()"
            case (
                1
            ):  # if it has a child, if the child is end parallel or end loop, ignore it, else add the child to the end of the command
                if str(self.children[0]) == "EndParallelGroup":
                    return f"new {str(self)}()"
                if str(self.children[0]) == "EndLoop":
                    return f"new {str(self)}()"
                return f"new {str(self)}(), {self.children[0].command()}"

    def runSim(self, time_start):
        # runs the correct actions during simulation
        if self.hasRun:  # if it has run,
            if (
                len(self.children) == 0
            ):  # if no children, return None to signal simulation is complete
                return None
            return self.children[0].runSim(
                time_start
            )  # otherwise run it's child's simulation and return it's result
        elif (
            time.time() > time_start + simDelay
        ):  # if not run and the current time is past the start time+the delay
            if (
                self.iters >= self.time
            ):  # if the iterations is more than the max number of iterations
                if (
                    self.iters >= simDuration
                ):  # if the iterations are more than the min duration of any block
                    self.iters = 0  # reset iterations
                    self.hasRun = True  # it has run
                    for (
                        i
                    ) in simItems:  # make sure all sim items are on integer grid lines
                        i.snapToGrid()
                    return (
                        time.time()
                    )  # return the current time which will be the start time for the next block
            else:  # if it hasn't finished the simulation,
                self.runSimBase()  # run this function (overrided by children classes)
            self.iters += 1
        return time_start  # return the start time to be passed back to this

    def runSimBase(self):
        # Does the action of the simulation, is implemented in child classes
        pass

    def resetSim(self, isLoopReset):
        # resets the hasRun properties of the blocks
        # if it is a loop reset, do not reset past the end loop block (implemented in end loop object)
        self.hasRun = False
        for i in self.children:
            i.resetSim(isLoopReset)


class TwoLineText(Object):
    # an visual object with two lines of text
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.initDraw()

    def initDraw(self):
        # should be overriden by the visual object
        self.textL1 = font.render("", True, black)
        self.textL2 = font.render("", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()

    def draw(self, surf):
        # create the background
        surf.blit(self, self.rect)
        # center the text on the object
        self.textRectL1.center = (
            (self.rect.width // 2) + self.rect.x,
            (self.rect.height // 2) + self.rect.y - 20,
        )
        self.textRectL2.center = (
            (self.rect.width // 2) + self.rect.x,
            (self.rect.height // 2) + self.rect.y + 20,
        )
        # add the text on top
        surf.blit(self.textL1, self.textRectL1)
        surf.blit(self.textL2, self.textRectL2)


class OneLineText(Object):
    # a visual object with one line of text
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.initDraw()

    def initDraw(self):
        # should be overwritten by the visual object
        self.textL1 = font.render("", True, black)
        self.textRectL1 = self.textL1.get_rect()

    def draw(self, surf):
        # create the background
        surf.blit(self, self.rect)
        # center the text
        self.textRectL1.center = (
            (self.rect.width // 2) + self.rect.x,
            (self.rect.height // 2) + self.rect.y,
        )
        # add the text on top
        surf.blit(self.textL1, self.textRectL1)


class ImageBase(Object):
    # a visual object with an image
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.initDraw()

    def initDraw(self):
        # should be overrwritten by the visual with correct image file
        self.img = pygame.image.load("BaseImage")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, self.rect.size)

    def draw(self, surf: pygame.Surface):
        # draw image
        surf.blit(self.img, self.rect)


class Draggable(TreeNode, Object):
    # creates an object that can be dragged by the user
    def __init__(self, size=(100, 100), pose=(500, 500)):
        super().__init__(size, pose)
        self.parent = None
        self.isParallel = (
            True  # initalize assuming it is parallel, but will be figured out later
        )
        # only used for sim below
        self.iters = 0
        self.time = 10
        self.distance = 1
        # (distance/time) * simBlockSize MUST be an INT 1/10 *50 = 5

    def drag(self, event):
        # drags the object with the movement of the mouse
        xvel = event.rel[0]
        yvel = event.rel[1]
        self.rect.x += xvel
        self.rect.y += yvel
        # don't drag above the top navigation
        if self.rect.y < topNav["height"] + 50:
            self.rect.y = topNav["height"] + 50
            pygame.mouse.set_pos((event.pos[0], topNav["height"] + 50))

    def snapToGrid(self):
        # snaps the object to the grid
        if not self.parent:
            # if no parent, just snap to the grid
            self.rect.centerx = (
                width - sideNav["width"] - sideSim["width"]
            ) // 2 + sideNav["width"]
            self.rect.x = round(self.rect.x / blockSize) * blockSize
            self.rect.y = round(self.rect.y / blockSize) * blockSize
        elif self.parent.numChild == 1:
            # if the parent has 1 child, ie. regular block
            # snap so x is aligned and y is 1 grid below the parent
            self.rect.centerx = self.parent.rect.centerx
            self.rect.top = self.parent.rect.bottom + blockSize
            self.isParallel = self.parent.isParallel
        elif self.parent.numChild == 2:
            # if the parent has 2 children, ie. parallel group
            self.isParallel = True  # this block is in parallel
            # if this block is on the left side of the parent, snap to left side else right side
            if (
                self.rect.centerx
                < (width - sideNav["width"] - sideSim["width"]) // 2 + sideNav["width"]
            ):
                self.rect.centerx = (
                    (width - sideNav["width"] - sideSim["width"]) / 4
                    + sideNav["width"]
                    + 5
                )
                self.rect.top = (
                    self.parent.rect.bottom + blockSize + 1
                )  # snap height slightly lower for consistency in height based functions
            else:
                self.rect.centerx = (
                    ((width - sideNav["width"] - sideSim["width"]) / 4) * 3
                    + sideNav["width"]
                    - 5
                )
                self.rect.top = self.parent.rect.bottom + blockSize

            self.rect.x = round(self.rect.x / blockSize) * blockSize


class Scrollable(Object):
    # Can be scrolled on the main section
    def __init__(self, size, pose):
        super().__init__(size, pose)
        # on init account for scroll
        self.rect.y = pose[1] - scrollY

    def draw(self, surf):
        # when drawing account for scroll
        self.rect.y += scrollY
        super().draw(surf)
        self.rect.y -= scrollY

    def collide(self, event):
        # when checking collisions, account for scroll
        x = event.pos[0]
        y = event.pos[1] - scrollY
        return self.rect.collidepoint((x, y))


class NavScrollable(Object):
    # Can be scrolled in the navigation bar (See Scrollable)
    def __init__(self, size, pose):
        super().__init__(size, pose)

    def draw(self, surf):
        self.rect.y += navScrollY
        super().draw(surf)
        self.rect.y -= navScrollY

    def collide(self, event):
        x = event.pos[0]
        y = event.pos[1] - navScrollY
        return self.rect.collidepoint((x, y))


class SimScrollable(Object):
    # Can be scrolled in the Simulation Field (See Scrollable)
    def __init__(self, size, pose):
        super().__init__(size, pose)

    def draw(self, surf):
        self.rect.y += simScrollY + topNav["height"]
        self.rect.x += simScrollX + (width - sideSim["width"])
        super().draw(surf)
        self.rect.y -= simScrollY + topNav["height"]
        self.rect.x -= simScrollX + (width - sideSim["width"])


class ObjectFactory(Object):
    # Generic Generator block. Will create a type of object at it's position on click
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.size = size  # save size and pose
        self.pose = pose

    def getObj(self, size, pose):
        # returns the correct object, (Implemented in child classes)
        pass

    def generate(self):  # generates the object on click
        global currDrag
        pose = (
            self.pose[0],
            self.pose[1] + navScrollY,
        )  # account for the navigation scroll in the pose of the new object
        item = self.getObj(self.size, pose)  # get the object
        dragItems.append(item)  # add it to the drag items, so it will be drawn
        currDrag = item  # make it being dragged currently


class Clickable(Object):
    # Generic Clickable Icon
    def __init__(self, size, pose):
        super().__init__(size, pose)

    def onClick():
        # Called when it is clicked (Implemented in child classes)
        pass


class Mobile(ImageBase):
    # Generic Sim Item that can be moved
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.direction = 3  # 0-right,1-down,2-left,3-up
        self.intakeOn = False
        self.intaked = None

    def moveDirection(self, vForward, vStrafe, vtheta, direction=None):
        # Move this obejct in a direction
        if (
            not direction
        ):  # if no direction given, use the current direction it is facing
            direction = round(self.direction)
        vx, vy = 0, 0  # convert to global vx and vy based on direction
        match (direction % 4):
            case 0:  # right
                vx, vy = vForward, vStrafe
            case 2:  # left
                vx, vy = vForward * -1, vStrafe * -1
            case 1:  # down
                vx, vy = -1 * vStrafe, vForward
            case 3:  # up
                vx, vy = vStrafe, vForward * -1
        self.move(vx, vy, vtheta)  # move in that direction

    def move(self, vX, vY, vtheta):
        # move in a global frame
        self.rect.x += vX * simBlockSize
        self.rect.y += vY * simBlockSize
        self.direction += vtheta
        self.direction = (
            4 + self.direction
            if self.direction < 0
            else self.direction - 4 if self.direction > 4 else self.direction
        )
        if self.intaked:  # if the robot has a note intaked
            print("movingIntaked")
            self.intaked.rect.center = self.rect.center  # keep the note with the robot
        self.checkCollisions(vX, vY)  # check if object is colliding with anything

    def draw(self, surf: pygame.Surface):
        # draw the images, rotated in the direction of the object
        img = pygame.transform.rotate(self.img, (self.direction * -90) - 90)
        rect = img.get_rect()
        rect.center = self.rect.center
        surf.blit(img, rect)

    def snapToGrid(self):
        # snap to grid of the simulation
        self.rect.x = round(self.rect.x / simBlockSize) * simBlockSize
        self.rect.y = round(self.rect.y / simBlockSize) * simBlockSize

    def checkCollisions(self, vx, vy):
        # Checks if this object is colliding with any other objects and moves if so.
        for i in simItems:
            # if it is checking against itself, or the robot (which is shooting a note) don't do anything
            # this will cause infinite recursion because it can't make them not collide
            if i == self or isinstance(i, RobotIcon) and i.isShooting:
                continue
            # if this object's rectangle is colliding with another
            if self.rect.colliderect(i.rect):
                # if the checked object is able to be moved
                if issubclass(type(i), Mobile):
                    # if the object is a note, and the intake is on, and the current object is the robot, and there is nothing in the intake
                    if (
                        isinstance(self, RobotIcon)
                        and self.intakeOn
                        and str(i) == "NoteIcon"
                        and not self.intaked
                    ):
                        if i.rect.collidepoint(
                            self.rect.center
                        ):  # once the note touches the center of the robot,
                            self.intaked = (
                                i  # save that object as the currently intaked
                            )
                            simItems.remove(i)  # stop drawing the note
                    else:  # otherwise move the mobile object
                        i.move(vx, vy, 0)
                else:  # if the object is not able to be moved
                    self.move(-1 * vx, -1 * vy, 0)  # move self backwards
                    if len(warnings) == 0:  # add a warning for moving into obstacles
                        warnings.append(Warning("Attempted to move into an obstacle"))


class Immobile(ImageBase):
    # Generic Simulation Item that Can't Move
    def __init__(self, size, pose):
        super().__init__(size, pose)

    def draw(self, surf: pygame.Surface):
        # center the image on the object's center and draw it
        rect = self.img.get_rect()
        rect.center = self.rect.center
        surf.blit(self.img, rect)

    def snapToGrid(self):
        self.rect.x = round(self.rect.x / simBlockSize) * simBlockSize
        self.rect.y = round(self.rect.y / simBlockSize) * simBlockSize


class UpButton(Scrollable, ImageBase, Draggable):
    # Up Button for the Changable Class, Has a parent of the changable it is on
    def __init__(self, pose, parent):
        super().__init__((25, 25), pose)  # always 25x25
        self.master = parent

    def initDraw(self):
        self.img = pygame.image.load("up.svg")  # draw the image of the up arrow
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, self.rect.size)

    def collide(self, event):  # when clicked, change the parent by 1
        val = super().collide(event)
        if val:
            self.master.changeItem(1)
        return val


class DownButton(Scrollable, ImageBase, Draggable):
    # Down Button for the Changable Class, Has a parent of the changable it is on
    def __init__(self, pose, parent):
        super().__init__((25, 25), pose)  # always 25x25
        self.master = parent

    def initDraw(self):
        self.img = pygame.image.load("down.svg")  # draw the image of the down arrow
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, self.rect.size)

    def collide(self, event):  # when clicked, change parent by -1
        val = super().collide(event)
        if val:
            self.master.changeItem(-1)
        return val


class Changable(Object):
    # An object that has a property that can be changed
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.item = (
            2 if not self.item else self.item
        )  # if the item hasn't been defined it's 2 otherwise use it's current value
        self.max = 10
        self.min = 1
        button1Pose = (
            self.rect.left,
            self.rect.bottom - 25,
        )  # calculate the poses of the buttons
        button2Pose = (self.rect.right - 25, self.rect.bottom - 25)
        self.buttonUp = UpButton(button1Pose, self)  # create the buttons
        self.buttonDown = DownButton(button2Pose, self)

    def changeItem(self, amt):
        # change the value of the stored item, clamping within bounds
        self.item += amt
        self.item = (
            self.max
            if self.item > self.max
            else self.min if self.item < self.min else self.item
        )
        self.initDraw()  # redo the drawing

    def draw(self, surf):
        super().draw(surf)  # draw this object then add the buttons on top
        self.buttonUp.rect.topleft = (self.rect.left, self.rect.bottom - 25)
        self.buttonDown.rect.topleft = (self.rect.right - 25, self.rect.bottom - 25)
        self.buttonUp.draw(surf)
        self.buttonDown.draw(surf)

    def collide(self, event):
        # checks if a click collides with the block
        a = super().collide(event)  # if it collides with the entire block
        b = self.buttonUp.collide(event)  # if it collides with the up button
        c = self.buttonDown.collide(event)  # if it collides with the down button
        return a and not b and not c  # it collides with the block and not the buttons

    def drag(self, event):
        # drag all three objects
        super().drag(event)
        self.buttonUp.drag(event)
        self.buttonDown.drag(event)


# ---------
# VISUALS
class ForwardVisual(TwoLineText):
    # The visual component of the Move Forward Block
    def __init__(self, size, pose):
        self.item = 1  # number of blocks to move forward
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((52, 185, 247))  # Color of the Block
        self.textL1 = font.render(f"Move {self.item}x", True, black)  # Text
        self.textL2 = font.render("Forward", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class BackwardVisual(TwoLineText):
    # The visual component of the Move Backward Block
    def __init__(self, size, pose):
        self.item = 1  # number of blocks to move backward
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((52, 185, 247))  # Color
        self.textL1 = font.render(f"Move {self.item}x", True, black)  # Text
        self.textL2 = font.render("Backward", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class StartVisual(OneLineText):
    # The visual component of the Start Block
    def initDraw(self):
        self.fill((45, 135, 50))  # Color
        self.textL1 = font.render("Start", True, black)  # Text
        self.textRectL1 = self.textL1.get_rect()


class ParallelGroupVisual(TwoLineText):
    # The visual component of the Parallel Group Block
    def initDraw(self):
        self.fill((120, 201, 215))  # Color
        self.textL1 = font.render("Parallel", True, black)  # Text
        self.textL2 = font.render("Group", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class EndParallelGroupVisual(TwoLineText):
    # The visual component of the End Parallel Group Block
    def initDraw(self):
        self.fill((120, 201, 215))
        self.textL1 = font.render("End", True, black)
        self.textL2 = font.render("Parallel", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class TurnLeftVisual(TwoLineText):
    # The visual component of the Turn Left Block
    def __init__(self, size, pose):
        self.item = 1
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((209, 135, 44))
        self.textL1 = font.render(f"Turn {self.item}x", True, black)
        self.textL2 = font.render("Left", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class TurnRightVisual(TwoLineText):
    # The visual component of the Turn Right Block
    def __init__(self, size, pose):
        self.item = 1
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((209, 135, 44))
        self.textL1 = font.render(f"Turn {self.item}x", True, black)
        self.textL2 = font.render("Right", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class LeftVisual(TwoLineText):
    # The visual component of the Move Left Block
    def __init__(self, size, pose):
        self.item = 1
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((52, 185, 247))
        self.textL1 = font.render(f"Move {self.item}x", True, black)
        self.textL2 = font.render("Left", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class RightVisual(TwoLineText):
    # The visual component of the Move Right Block
    def __init__(self, size, pose):
        self.item = 1
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((52, 185, 247))
        self.textL1 = font.render(f"Move {self.item}x", True, black)
        self.textL2 = font.render("Right", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class IntakeStartVisual(TwoLineText):
    # The visual component of the Intake Start Block
    def initDraw(self):
        self.fill((152, 116, 242))
        self.textL1 = font.render("Intake", True, black)
        self.textL2 = font.render("Start", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class IntakeStopVisual(TwoLineText):
    # The visual component of the Intake Stop Block
    def initDraw(self):
        self.fill((152, 116, 242))
        self.textL1 = font.render("Intake", True, black)
        self.textL2 = font.render("Stop", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class ShootVisual(OneLineText):
    # The visual component of the Shoot Block
    def initDraw(self):
        self.fill((245, 132, 215))
        self.textL1 = font.render("Shoot", True, black)
        self.textRectL1 = self.textL1.get_rect()


class LoopVisual(TwoLineText):
    # The visual component of the Loop Block
    def __init__(self, size, pose):
        self.item = 2
        super().__init__(size, pose)

    def initDraw(self):
        self.fill((120, 201, 215))
        self.textL1 = font.render("Loop", True, black)
        self.textL2 = font.render(f"{self.item}x", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


class EndLoopVisual(TwoLineText):
    # The visual component of the End Loop Block. Extends Two Line Text
    def initDraw(self):
        self.fill((120, 201, 215))
        self.textL1 = font.render("End", True, black)
        self.textL2 = font.render("Loop", True, black)
        self.textRectL1 = self.textL1.get_rect()
        self.textRectL2 = self.textL2.get_rect()


# ---------
# OBJECTS - Extend Changable (sometimes), Scrollable, Relative Visual, Draggable
class ForwardObject(Changable, Scrollable, ForwardVisual, Draggable):
    # Move Forward Object
    def __str__(self):
        return "MoveForward"

    def runSimBase(self):
        self.distance = self.item  # move the chosen distance
        self.time = 50 * self.item  # take 50 iterations per block moved
        simItems[0].moveDirection(
            self.distance / self.time, 0, 0
        )  # move the correct distance/time


class BackwardObject(Changable, Scrollable, BackwardVisual, Draggable):
    # Move Backward Object (See ForwardObject)
    def __str__(self):
        return "MoveBackward"

    def runSimBase(self):
        self.distance = self.item
        self.time = 50 * self.item
        simItems[0].moveDirection(
            -1 * (self.distance / self.time), 0, 0
        )  # move backward


class StartObject(TreeNode, Scrollable, StartVisual):
    # Start Object
    def __init__(self):
        # Put it in the correct position. in the middle of the main area and 1 grid below the top navigation
        super().__init__(
            (180, 100),
            (
                (width - sideNav["width"] - sideSim["width"]) // 2
                + sideNav["width"]
                - 90,
                topNav["height"] + blockSize,
            ),
        )
        self.rect.x = round(self.rect.x / blockSize) * blockSize  # snap to grid
        self.time = 1

    def __str__(self):
        return "Start"

    def collide(self, event):
        return False  # can't click it

    def drag(self, event):
        pass  # can't drag it

    def snapToGrid(self):
        self.rect.centerx = (
            width - sideNav["width"] - sideSim["width"]
        ) // 2 + sideNav[
            "width"
        ]  # snap to the center of the main area

    def findParents(self):
        pass  # no parents

    def command(self):
        match len(self.children):
            case (
                1
            ):  # if any children, make a new sequential command group and add the commands of the child
                return f"new SequentialCommandGroup({self.children[0].command()});"
            case 0:
                return ""

    def runSim(self, time_start):
        # do nothing in sim (See TreeNode for typical implementation)
        if self.hasRun:
            if len(self.children) == 0:
                return None
            return self.children[0].runSim(time_start)
        elif time.time() > time_start:  # if time is past the start time it has finished
            self.hasRun = True
            return time.time()
        return time_start

    def resetSim(self, isLoopReset):
        self.hasRun = False
        for i in self.children:  # reset all blocks
            i.resetSim(isLoopReset)


class ParallelObject(Scrollable, ParallelGroupVisual, Draggable):
    # Parallel Group Object
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.numChild = 2  # default 2

    def __str__(self):
        return "ParallelGroup"

    def snapToGrid(self):
        # always center the group and put it right below the parent if it exists
        self.rect.centerx = (
            width - sideNav["width"] - sideSim["width"]
        ) // 2 + sideNav["width"]
        if not self.parent:
            self.rect.y = round(self.rect.y / blockSize) * blockSize
        else:
            self.rect.top = self.parent.rect.bottom + blockSize

    def findParents(self):
        # finds the parent node of this object
        # the parent is the closest node vertically above the object
        # if the parent is parallel, the center of the object must be within the parent block (x-axis only)
        parent = None
        amountAbove = math.inf
        for i in dragItems:
            above = self.rect.y - i.rect.y
            if above > 0 and above < amountAbove:
                parent = i
                amountAbove = above
        self.parent = parent
        if not self in self.parent.children:
            self.parent.children += (self,)
        # if parent is an endparallel, find the parallel above it and add self to the other child of that parallel group
        if str(self.parent) == "EndParallelGroup":
            item = self.parent
            while True:
                if item == None:
                    break
                if str(item) == "ParallelGroup":
                    item.otherChild = self
                    break
                item = item.parent
        # if parent is an endloop, find the loop above it and add self to the other child of that loop group
        if str(self.parent) == "EndLoop":
            item = self.parent
            while True:
                if item == None:
                    break
                if str(item) == "Loop":
                    item.otherChild = self
                    break
                item = item.parent

    def command(self):
        # makes the command to convert to java
        s = ""
        if (
            len(self.children) == 2
        ):  # when have two children, put them into sequential groups in a parallel group
            s += f"new ParallelCommandGroup(new SequentialCommandGroup({self.children[0].command()}), new SequentialCommandGroup({self.children[1].command()}))"
        elif (
            len(self.children) == 1 and str(self.children[0]) != "EndParallelGroup"
        ):  # when has 1 child and it's not a end parallel group
            s += f"new ParallelCommandGroup(new SequentialCommandGroup({self.children[0].command()}))"  # put into a sequential group
        if (
            self.otherChild and len(self.children) != 0
        ):  # if there is a child below the end parallel group and there are non-zero children
            s += (
                f", {self.otherChild.command()}"  # add a comma and the child's commands
            )
        elif (
            self.otherChild
        ):  # if there are no children and but there is a child below the end parallel group, just add the child's command
            s += f"{self.otherChild.command()}"
        return s

    def runSim(self, time_start):
        # Run the simulation
        match len(self.children):
            case 0:  # if there are no children
                pass
            case 1:  # if there is 1 child
                output = self.children[0].runSim(time_start)  # run the sim on that
                if output:  # if not None
                    return output  # return that
            case 2:
                output1 = self.children[0].runSim(time_start)
                output2 = self.children[1].runSim(time_start)
                if output1 and output2:  # if both are not None
                    return (
                        output1 if output1 > output2 else output2
                    )  # return the bigger one
                if output1:
                    return output1
                if output2:
                    return output2
        if self.otherChild:
            return self.otherChild.runSim(time_start)
        return None


class EndParallelObject(Scrollable, EndParallelGroupVisual, Draggable):
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.numChild = 1
        self.parents = []

    def __str__(self):
        return "EndParallelGroup"

    def findParents(self):
        print("end")
        self.isParallel = False
        parents = []
        amountAbove = math.inf
        for i in dragItems:
            above = self.rect.y - i.rect.y
            if above > 0 and above < amountAbove:
                parent = [i]
                amountAbove = above
            elif above > 0 and above == amountAbove:
                parent.append(i)
        self.parent = parent[0]
        self.parents = parent
        for i in parent:
            if not self in i.children:
                i.children += (self,)

    def snapToGrid(self):
        self.rect.centerx = (
            width - sideNav["width"] - sideSim["width"]
        ) // 2 + sideNav["width"]
        if not self.parent:
            self.rect.y = round(self.rect.y / blockSize) * blockSize
        else:
            self.rect.top = self.parent.rect.bottom + blockSize

    def command(self):
        return ""

    def runSim(self, time_start):
        return None


class LeftObject(Changable, Scrollable, LeftVisual, Draggable):
    # Move Left Object (See ForwardObject)
    def __str__(self):
        return "MoveLeft"

    def runSimBase(self):
        self.distance = self.item
        self.time = 50 * self.item
        simItems[0].moveDirection(0, -1 * (self.distance / self.time), 0)


class RightObject(Changable, Scrollable, RightVisual, Draggable):
    # Move Right Object (See ForwardObject)
    def __str__(self):
        return "MoveRight"

    def runSimBase(self):
        self.distance = self.item
        self.time = 50 * self.item
        simItems[0].moveDirection(0, (self.distance / self.time), 0)


class TurnLeftObject(Changable, Scrollable, TurnLeftVisual, Draggable):
    # Turn Left Object (See ForwardObject)
    def __str__(self):
        return "TurnLeft"

    def runSimBase(self):
        self.distance = self.item
        self.time = 45 * self.item
        simItems[0].moveDirection(0, 0, -1 * (self.distance / self.time))


class TurnRightObject(Changable, Scrollable, TurnRightVisual, Draggable):
    # Turn Right Object (See ForwardObject)
    def __str__(self):
        return "TurnRight"

    def runSimBase(self):
        self.distance = self.item
        self.time = 45 * self.item
        simItems[0].moveDirection(0, 0, (self.distance / self.time))


class IntakeStartObject(Scrollable, IntakeStartVisual, Draggable):
    # Intake Start Object
    def __str__(self):
        return "IntakeStart"

    def runSimBase(self):
        simItems[0].intakeOn = True  # turn on intake
        simItems[0].initDraw()  # reload Robot Icon Image


class IntakeStopObject(Scrollable, IntakeStopVisual, Draggable):
    # Intake Stop Object
    def __str__(self):
        return "IntakeStop"

    def runSimBase(self):
        simItems[0].intakeOn = False
        simItems[0].initDraw()  # reload Robot Icon Image


class ShootObject(Scrollable, ShootVisual, Draggable):
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.distance = 4
        self.time = 50
        # distance/time *50 must be int
        # 4/40*50 = 5
        # 2/50*50 = 2

    def __str__(self):
        return "Shoot"

    def runSim(self, time_start):
        # Run Simulation See TreeNode for complete comments
        if self.hasRun:
            if len(self.children) == 0:
                return None
            return self.children[0].runSim(time_start)
        elif time.time() > time_start + simDelay:
            if (
                self.iters >= self.time or not simItems[0].intaked
            ):  # don't do anything if nothing is intaked
                if self.iters >= simDuration:
                    self.iters = 0
                    super().runSim(time.time())
                    self.hasRun = True
                    simItems[0].intaked = None  # no longer has anything intaked
                    simItems[0].isShooting = False  # no longer shooting
                    return time.time()
            else:
                simItems[0].isShooting = True  # it is shooting
                simItems[0].intaked.moveDirection(
                    (self.distance) / self.time, 0, 0, round(simItems[0].direction)
                )  # move the note in the direction of the robot
                if self.iters == 0:
                    simItems.append(simItems[0].intaked)  # add to sim items only once
            self.iters += 1
        return time_start


class LoopObject(Changable, Scrollable, LoopVisual, Draggable):
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.numChild = 1
        self.currLoop = 1  # current loop
        self.initDraw()

    def __str__(self):
        return "Loop"

    def command(self):
        s = ""
        if len(self.children) == 1:
            s += self.children[0].command() + ", "
            s *= self.item
            s = s[0:-2]
            if self.otherChild:
                s += f", {self.otherChild.command()}"
        elif self.otherChild:
            s += f"{self.otherChild.command()}"
        return s

    def resetSim(self, isLoopReset):
        self.currLoop = 1
        for i in self.children:
            i.resetSim(isLoopReset)

    def runSim(self, time_start):
        match len(self.children):
            case 0:
                pass
            case 1:
                output = self.children[0].runSim(time_start)
                if output:  # if not None
                    return output
                if self.currLoop < self.item:
                    self.children[0].resetSim(True)
                    self.currLoop += 1
                    return time.time()
        if self.otherChild:
            return self.otherChild.runSim(time_start)
        return None


class EndLoopObject(Scrollable, EndLoopVisual, Draggable):
    def __init__(self, size, pose):
        super().__init__(size, pose)
        self.numChild = 1

    def __str__(self):
        return "EndLoop"

    def command(self):
        return ""

    def resetSim(self, isLoopReset):
        if not isLoopReset:
            for i in self.children:
                i.resetSim(False)

    def runSim(self, time_start):
        if self.hasRun:
            if len(self.children) == 0:
                return None
            return self.children[0].runSim(time_start)
        elif time.time() > time_start:
            super().runSim(time.time())
            self.hasRun = True
            return time.time()
        else:
            return time_start


# ---------
# FACTORIES
class ParallelFactory(NavScrollable, ParallelGroupVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return ParallelObject((420, 100), pose)


class EndParallelFactory(NavScrollable, EndParallelGroupVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return EndParallelObject((420, 100), pose)


class ForwardFactory(NavScrollable, ForwardVisual, ObjectFactory):
    def __init__(self, num):
        ObjectFactory.__init__(self, (180, 100), (30, 120 * num))
        ForwardVisual.initDraw(self)

    def getObj(self, size, pose):
        return ForwardObject(size, pose)


class BackwardFactory(NavScrollable, BackwardVisual, ObjectFactory):
    def __init__(self, num):
        ObjectFactory.__init__(self, (180, 100), (30, 120 * num))
        BackwardVisual.initDraw(self)

    def getObj(self, size, pose):
        return BackwardObject(size, pose)


class LeftFactory(NavScrollable, LeftVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return LeftObject(size, pose)


class RightFactory(NavScrollable, RightVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return RightObject(size, pose)


class TurnLeftFactory(NavScrollable, TurnLeftVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return TurnLeftObject(size, pose)


class TurnRightFactory(NavScrollable, TurnRightVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return TurnRightObject(size, pose)


class IntakeStartFactory(NavScrollable, IntakeStartVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return IntakeStartObject(size, pose)


class IntakeStopFactory(NavScrollable, IntakeStopVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return IntakeStopObject(size, pose)


class ShootFactory(NavScrollable, ShootVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return ShootObject(size, pose)


class LoopFactory(NavScrollable, LoopVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return LoopObject((220, 100), pose)


class EndLoopFactory(NavScrollable, EndLoopVisual, ObjectFactory):
    def __init__(self, num):
        super().__init__((180, 100), (30, 120 * num))

    def getObj(self, size, pose):
        return EndLoopObject((260, 100), pose)


# ---------
# NAV ICONS
class GenerateCode(ImageBase, Clickable):
    def __init__(self, num):
        super().__init__((50, 50), (25 + 75 * num, 25))

    def onClick(self):
        s = ""
        try:
            with open("javaIn.java", "r") as file:
                s += file.read()
                file.close()
        except:
            warnings.append(Warning("javaIn.java File Not Found"))
            return
        index = s.find("// ADDCOMMANDSHERE!!!")
        if index < 0:
            warnings.append(Warning("Comment not found in javaIn.java file"))
            return
        s = s[:index] + generateCommands() + s[index + 20 :]
        with open("javaOut.java", "w") as file:
            file.write(s)
            file.close()
        if len(warnings) == 0:
            successes.append(Success("Successfully wrote to the Java File"))

    def initDraw(self):
        self.img = pygame.image.load("java.png")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))


class RunSim(ImageBase, Clickable):
    def __init__(self, num):
        super().__init__((50, 50), (25 + 75 * num, 25))

    def onClick(self):
        global currSim, simStartTime
        if not currSim and not dragItems[0].hasRun:
            currSim = True
            simStartTime = time.time()
            self.img = pygame.image.load("playDark.svg")
            self.imgRect = self.img.get_rect()
            pygame.transform.scale(self.img, (simBlockSize, simBlockSize))

    def initDraw(self):
        self.img = pygame.image.load("play.svg")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))


class Reset(ImageBase, Clickable):
    def __init__(self, num):
        super().__init__((50, 50), (25 + 75 * num, 25))

    def onClick(self):
        global currSim, simItems, warnings
        currSim = False
        simItems = generateSim(classes)
        warnings = []
        for i in clickItems:
            if type(i) == RunSim:
                i.initDraw()
        dragItems[0].resetSim(False)

    def initDraw(self):
        self.img = pygame.image.load("reset.png")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))


class Validate(ImageBase, Clickable):
    def __init__(self, num):
        super().__init__((50, 50), (25 + 75 * num, 25))

    def initDraw(self):
        self.img = pygame.image.load("validate.png")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))

    def onClick(self):
        global warnings, successes
        warnings = []
        successes = []
        openParallels = 0
        openLoops = 0
        for i in dragItems:
            if str(i) == "ParallelGroup":
                if openParallels == 1:
                    warnings.append(Warning("Missing EndParallelGroup"))
                else:
                    openParallels += 1
            if str(i) == "EndParallelGroup":
                if openParallels == 0:
                    warnings.append(Warning("Extra EndParallelGroup found"))
                else:
                    openParallels -= 1
            if str(i) == "Loop":
                if openLoops == 1:
                    warnings.append(Warning("Missing EndLoop"))
                else:
                    openLoops += 1
            if str(i) == "EndLoop":
                if openLoops == 0:
                    warnings.append(Warning("Extra EndLoop found"))
                else:
                    openLoops -= 1
        if openParallels == 1:
            warnings.append(Warning("Missing EndParallelGroup"))
        if openLoops == 1:
            warnings.append(Warning("Missing EndLoop"))
        if len(warnings) == 0:
            successes.append(Success("Successfully Verified!"))


# ---------
# SIM ICONS
class RobotIcon(SimScrollable, Mobile):
    def __init__(self, pose):
        x = pose[0] * simBlockSize
        y = pose[1] * simBlockSize
        self.intakeOn = False
        self.imgIntakeOff = pygame.image.load("robotIconOff.svg")
        self.imgIntakeOn = pygame.image.load("robotIconOn.svg")
        super().__init__((simBlockSize, simBlockSize), (x, y))
        self.intaked = None
        self.isShooting = False

    def initDraw(self):
        if self.intakeOn:
            self.img = self.imgIntakeOn
        else:
            self.img = self.imgIntakeOff
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))

    def __str__(self):
        return "RobotIcon"


class NoteIcon(SimScrollable, Mobile):
    def __init__(self, pose):
        x = pose[0] * simBlockSize
        y = pose[1] * simBlockSize
        super().__init__((simBlockSize, simBlockSize), (x, y))

    def __str__(self):
        return "NoteIcon"

    def initDraw(self):
        self.img = pygame.image.load("noteIcon.svg")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))


class ObstacleIcon(SimScrollable, Immobile):
    def __init__(self, pose):
        x = pose[0] * simBlockSize
        y = pose[1] * simBlockSize
        super().__init__((simBlockSize, simBlockSize), (x, y))

    def __str__(self):
        return "ObstacleIcon"

    def initDraw(self):
        self.img = pygame.image.load("obstacleIcon.svg")
        self.imgRect = self.img.get_rect()
        pygame.transform.scale(self.img, (simBlockSize, simBlockSize))


# ---------
# MISC OBJECTS
class Warning(Object):
    def __init__(self, content):
        if len(warnings) == 0:
            pose = (400, 200)
        else:
            pose = (400, warnings[-1].rect.bottom + 20)
        self.initDraw(content)
        super().__init__((500, len(self.textRects) * 30 + 20), pose)

    def initDraw(self, content):
        lis = content.split(" ")
        lines = [[]]
        currLine = 0
        currCount = 0
        for word in lis:
            currCount += len(word) + 1
            if currCount > 25:
                lines.append([])
                currCount = 0
                currLine += 1
            lines[currLine].append(word)
        self.textLs = []
        self.textRects = []
        for line in lines:
            line = " ".join(line)
            self.textLs.append(font.render(line, True, black))
            self.textRects.append(self.textLs[-1].get_rect())

    def draw(self, surf):
        self.fill((200, 45, 50))
        self.set_alpha(200)
        surf.blit(self, self.rect)
        for i in range(len(self.textRects)):
            offset = i * 30
            self.textRects[i].center = (self.rect.centerx, self.rect.top + offset + 25)
            surf.blit(self.textLs[i], self.textRects[i])


class Success(Object):
    def __init__(self, content):
        if len(warnings) == 0:
            pose = (400, 200)
        else:
            pose = (400, warnings[-1].rect.bottom + 20)
        self.initDraw(content)
        super().__init__((500, len(self.textRects) * 30 + 20), pose)

    def initDraw(self, content):
        lis = content.split(" ")
        lines = [[]]
        currLine = 0
        currCount = 0
        for word in lis:
            currCount += len(word) + 1
            if currCount > 25:
                lines.append([])
                currCount = 0
                currLine += 1
            lines[currLine].append(word)
        self.textLs = []
        self.textRects = []
        for line in lines:
            line = " ".join(line)
            self.textLs.append(font.render(line, True, black))
            self.textRects.append(self.textLs[-1].get_rect())

    def draw(self, surf):
        self.fill((45, 200, 50))
        self.set_alpha(200)
        surf.blit(self, self.rect)
        for i in range(len(self.textRects)):
            offset = i * 30
            self.textRects[i].center = (self.rect.centerx, self.rect.top + offset + 25)
            surf.blit(self.textLs[i], self.textRects[i])


# ------------
# GENERAL PURPOSE FUNCTIONS
def printTree():
    for pre, fill, node in RenderTree(dragItems[0]):
        print("%s%s" % (pre, str(node)))


def generateCommands():
    return dragItems[0].command()


blockSize = 20  # Set the size of the grid block


def drawGrid():
    for x in range(sideNav["width"], width - sideSim["width"], blockSize):
        for y in range(
            topNav["height"] - blockSize * 3, height + blockSize * 3, blockSize
        ):
            rect = pygame.Rect(x, y + (scrollY % (blockSize * 2)), blockSize, blockSize)
            pygame.draw.rect(screen, white, rect, 1)


simBlockSize = 50


def drawGrid2():
    for x in range(
        width - sideSim["width"] - simBlockSize * 3,
        width + simBlockSize * 3,
        simBlockSize,
    ):
        for y in range(
            topNav["height"] - simBlockSize * 3, height + simBlockSize * 3, simBlockSize
        ):
            rect = pygame.Rect(
                x + (simScrollX % (simBlockSize * 2)),
                y + (simScrollY % (simBlockSize * 2)),
                simBlockSize,
                simBlockSize,
            )
            pygame.draw.rect(screen, white, rect, 1)


def generateSim(classes: list):
    simItems = []
    filename = "simSetup.txt"
    try:
        with open(filename, "r") as file:
            for line in file.readlines():
                if len(line) == 0:
                    continue
                lis = line.split(",")
                if len(lis) < 3:
                    print(
                        f"Error with importing {filename}, ensure that all lines have 3 items seperated by commas"
                    )
                    exit()
                pose = (int(lis[1]), int(lis[2]))
                obj = None
                for i in classes:
                    if lis[0] == i.__name__:
                        obj = i(pose)
                        simItems.append(obj)
                        break
                if not obj:
                    print(
                        f"Error with importing {filename}, ensure that all lines have a correct Name."
                    )
                    exit()
            file.close()
        return simItems
    except:
        print(f"simSetup.txt is missing")
        exit()


# ----------
# RUNTIME VARIABLES
mouse = [0, 0]
openParallels = 0
bg = 185, 192, 230
# Scrolling
# max values are 0 because a reasonable scroll is negative. This is because the scroll moves the "origin",
# but pos y would move the origin down, and the content down
scrollY = 0
navScrollY = 0
simScrollY = 0
simScrollX = 0
# NavBarTop
topNav = {
    "height": 100,
    "bg": (100, 100, 125),
}
# NavBarLeft
sideNav = {
    "width": 240,
    "bg": (150, 150, 150),
}
# SimBarRight
sideSim = {"maxWidth": 800, "width": 800, "bg": (224, 191, 92)}
# Colors
black = (0, 0, 0)
white = (255, 255, 255)
# Timing
iteration = 1
start = time.time_ns()
# Dragging
currDrag = None
backgroundDrag = False
navDrag = False
simDrag = False
# Items
grabItems = [
    ForwardFactory(1),
    BackwardFactory(2),
    LeftFactory(3),
    RightFactory(4),
    TurnLeftFactory(5),
    TurnRightFactory(6),
    IntakeStartFactory(7),
    IntakeStopFactory(8),
    ShootFactory(9),
    LoopFactory(10),
    EndLoopFactory(11),
    ParallelFactory(12),
    EndParallelFactory(13),
]
dragItems = [StartObject()]
clickItems = [GenerateCode(0), Validate(1), RunSim(2), Reset(3)]
warnings = []
successes = []
# Simulation
currSim = False
simDelay = 0.1
simDuration = 50
currSimItems = []
timeSinceLastClick = 0
simStartTime = None
# MaxScrolling
maxScroll = 0
for i in grabItems:
    b = i.rect.bottom
    if b > maxScroll:
        maxScroll = b
maxScroll += 20
classes = [RobotIcon, NoteIcon, ObstacleIcon]  # sim classes
simItems = generateSim(classes)
# Start the window
screen = pygame.display.set_mode(size, pygame.RESIZABLE, pygame.SRCALPHA)
while True:
    # ---------
    # LOGIC
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and timeSinceLastClick > 20
        ):
            timeSinceLastClick = 0  # reset click timer
            for i in clickItems:  # if you click a nav item, run their onClick Function
                if i.collide(event):
                    i.onClick()
                    break
            for i in grabItems:  # if you click a factory, generate a new drag item
                if i.collide(event) and not currSim and event.pos[1] > topNav["height"]:
                    i.generate()
                    break
            for i in dragItems:  # if you click a draggable item, start dragging it
                if i.collide(event) and not currSim and event.pos[1] > topNav["height"]:
                    currDrag = i
                    break
            for i in warnings:  # if you click a warning, get rid of it
                if i.collide(event):
                    warnings.remove(i)
                    del i
            for i in successes:  # if you click a success message, get rid of it
                if i.collide(event):
                    successes.remove(i)
                    del i
            # if you don't click anything you can drag and you are within one of the three draggable areas, start dragging it
            if (
                not currDrag
                and event.pos[0] > sideNav["width"]
                and event.pos[0] < width - sideSim["width"]
                and event.pos[1] > topNav["height"]
            ):
                backgroundDrag = True
            elif (
                not currDrag
                and event.pos[0] < sideNav["width"]
                and event.pos[1] > topNav["height"]
            ):
                navDrag = True
            elif (
                not currDrag
                and event.pos[0] > (width - sideSim["width"])
                and event.pos[1] > topNav["height"]
            ):
                simDrag = True
        if event.type == pygame.MOUSEMOTION:
            # update mouse position
            mouse = event.pos
            if currDrag:  # if dragging an item, move it
                currDrag.drag(event)
            if backgroundDrag:  # if dragging a zone, move it
                scrollY += event.rel[1]
            if navDrag:
                navScrollY += event.rel[1]
            if simDrag:
                simScrollX += event.rel[0]
                simScrollY += event.rel[1]
        if event.type == pygame.MOUSEBUTTONUP:
            if currDrag:
                # remove it if its past the edge on either side
                if currDrag.rect.centerx < sideNav["width"] or currDrag.rect.centerx > (
                    width - sideSim["width"]
                ):
                    dragItems.remove(currDrag)
                    del currDrag
                # find the parents of all the items on the board
                for i in dragItems:
                    i.children = ()
                for i in dragItems:
                    i.findParents()
                # snap all items to the grid
                for i in dragItems:
                    i.snapToGrid()
                # reorder list by y value
                newDict = {}
                keys = []
                for i in dragItems:
                    newDict[i.rect.top] = i
                    keys.append(i.rect.top)
                keys.sort()
                newList = []
                for key in keys:
                    newList.append(newDict[key])
                dragItems = newList
            # Nothing is being dragged
            currDrag = None
            backgroundDrag = False
            navDrag = False
            simDrag = False
        if event.type == pygame.MOUSEWHEEL:
            # scroll the correct area based on mouse location
            if mouse[0] < sideNav["width"]:
                navScrollY += (abs(event.precise_y) ** (1 / 4.0)) * 10 * event.y
            elif mouse[0] < width - sideSim["width"]:
                scrollY += (abs(event.precise_y) ** (1 / 4.0)) * 10 * event.y
            else:
                simScrollX -= (abs(event.precise_x) ** (1 / 4.0)) * 10 * event.x
                simScrollY += (abs(event.precise_y) ** (1 / 4.0)) * 10 * event.y
        if event.type == pygame.WINDOWRESIZED:
            # when resizing windows make sure to update the size of all zones porportionally
            size = width, height = screen.get_size()
            sideSim["width"] = sideSim["maxWidth"]
            sideSim["width"] = (
                (width - sideNav["width"] - 420)
                if sideSim["width"] > (width - sideNav["width"] - 420)
                else sideSim["width"]
            )
            sideSim["width"] -= blockSize - (
                width - sideSim["width"] - sideNav["width"]
            ) % (
                blockSize * 2
            )  # do not allow partial grids in block area
            # find all children and snap to grid
            for i in dragItems:
                i.children = ()
            for i in dragItems:
                i.findParents()
            for i in dragItems:
                i.snapToGrid()
    if not currDrag:
        # snap to grid if not doing anything else
        for i in dragItems:
            i.snapToGrid()
    scrollY = scrollY if scrollY < 0 else 0  # dont scroll above the start object
    navScrollY = (
        navScrollY if navScrollY < 0 else 0
    )  # dont scroll above the first item in the nav bar
    navScrollY = (
        navScrollY
        if navScrollY > -1 * (maxScroll - height)
        else -1 * (maxScroll - height)
    )  # dont scroll below the last item in the nav bar
    if currSim:
        # if the simStartTime exists (not None)
        if simStartTime:
            # run the recursive sim. It returns the start time of the next command if it is not complete and None once fully completed
            simStartTime = dragItems[0].runSim(simStartTime)
        else:
            # once done, not sim anymore
            currSim = False
    # ---------
    # DRAW
    screen.fill(bg)
    # SideSim
    pygame.draw.rect(
        screen,
        sideSim["bg"],
        pygame.Rect(
            width - sideSim["width"],
            topNav["height"],
            sideSim["width"],
            height - topNav["height"],
        ),
    )
    drawGrid2()
    for i in simItems:
        i.draw(screen)
    # MainArea
    pygame.draw.rect(screen, bg, pygame.Rect(0, 0, width - sideSim["width"], height))
    drawGrid()
    # SideNav
    pygame.draw.rect(
        screen,
        sideNav["bg"],
        pygame.Rect(0, topNav["height"], sideNav["width"], height - topNav["height"]),
    )
    for i in grabItems:
        i.draw(screen)
    # main board items
    for i in dragItems:
        i.draw(screen)
    # draw top navigation
    pygame.draw.rect(screen, topNav["bg"], pygame.Rect(0, 0, width, topNav["height"]))
    for i in clickItems:
        i.draw(screen)
    # draw warnings
    for i in warnings:
        i.draw(screen)
    # draw successes
    for i in successes:
        i.draw(screen)
    # ----------------
    # Keep display code above
    # show new content
    pygame.display.flip()
    # incremement iterators
    timeSinceLastClick += 1
    iteration += 1
    if iteration % 1000 == 0:  # keep track of loop timing
        end = time.time_ns()
        print(
            "1000 iterations took: "
            + str(round((end - start) / 1_000_000 / 1_000, 3))
            + " ms each"
        )
        start = time.time_ns()
pygame.quit()
