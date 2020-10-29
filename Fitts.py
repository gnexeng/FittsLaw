from tkinter import *
from random import randint, shuffle
from math import sqrt
from time import time
import sqlite3
#from winsound import PlaySound, Beep
from pathlib import Path
from shutil import copyfile
#from win32api import SetCursorPos


class SQLHandler():
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # change working dir to directory of script
    db_path = "database.sqlite"
    # copy database from source database if needed
    if not Path(db_path).exists():
        copyfile("default.sqlite", db_path)

    @staticmethod
    def getMasterBlock():
        # connect to database, grab the unique tasks, then close
        block = list()
        db = sqlite3.connect(SQLHandler.db_path)
        curs = db.cursor()
        for row in curs.execute('SELECT * FROM tasks'):
            block.append(row)
        db.close()
        return block

    @staticmethod
    def addUser(participant):
        db = sqlite3.connect(SQLHandler.db_path)
        curs = db.cursor()

        # Find participant's record by id
        participant_id = curs.execute('INSERT INTO participants DEFAULT VALUES').lastrowid  # creates auto userID
        # execute UPDATE Command here to modify the record

        db.commit()
        db.close()

        return participant_id




    @staticmethod
    def insertTrialData(trial_data, participant_id):
        print(participant_id)
        db = sqlite3.connect(SQLHandler.db_path)
        curs = db.cursor()


        for block in trial_data.keys():
            block_start_time = trial_data[block]["block_start_time"]
            block_end_time = trial_data[block]["block_end_time"]
            trial_data[block].pop("block_end_time")
            trial_data[block].pop("block_start_time")
            values = [participant_id, block_start_time, block_end_time]
            block_id = curs.execute('INSERT INTO blocks (participant_id, started_at, finished_at) VALUES (?,?,?)',
                                    values).lastrowid

            print("block: ", block)
            for trial in trial_data[block].keys():
                task_id = trial[0]
                errors = trial_data[block][trial]["errors"]
                distance = int(trial_data[block][trial]["distance"])
                start_time = trial_data[block][trial]["start_time"]
                end_time = trial_data[block][trial]["end_time"]
                values = [block_id, task_id, start_time, end_time, distance, errors, participant_id]
                curs.execute(
                    'INSERT INTO trials (block_id,task_id,started_at,finished_at,distance_travelled,errors, participant_id) VALUES (?,?,?,?,?,?,?)',
                    values)
            trial_data[block]["block_start_time"] = block_start_time
            trial_data[block]["block_end_time"] = block_end_time
        db.commit()
        db.close()

    @staticmethod
    def closeDB():
        SQLHandler.db.close()


class Participant:
    def __init__(self):
        self.id = None
        self.age = None
        self.gender = None
        self.handedness = None
        self.average_comp_usage = None
        self.input_device = None


class Trials:
    def __init__(self):
        self.trial_data = dict()  # contains all trial data made by user
        self.current_trial = None  # tuple containing current task
        self.block = SQLHandler.getMasterBlock()  # generate a source block with all permutations
        self.current_block = list()  # current block of tasks; empty to make new block
        self.max_blocks = 1  # number of blocks in program
        self.block_countdown = self.max_blocks  # number of blocks left to do
        self.mouse_lastx = 0  # position of last mouse x
        self.mouse_lasty = 0  # position of last mouse x
        self.trial_counter = 0  # simple counter used for number of trials complete
        self.trial_max = len(self.block) * self.max_blocks

    def getNextTrial(self):
        if (len(self.current_block) > 0):
            self.current_trial = self.current_block.pop()  # get the next trial tuple
        else:
            # start of new block
            self.block_countdown -= 1

            if self.block_countdown >= 0:
                self.current_block = list(self.block)
                shuffle(self.current_block)  # randomize the order
                self.current_trial = self.current_block.pop()  # get the next trial tuple
                self.trial_data[self.block_countdown] = dict()
                self.trial_data[self.block_countdown]["block_start_time"] = time()
            else:
                return None  # experiment over

        self.trial_counter += 1
        self.trial_data[self.block_countdown][self.current_trial] = dict()
        self.trial_data[self.block_countdown][self.current_trial]["errors"] = 0
        self.trial_data[self.block_countdown][self.current_trial]["distance"] = 0
        self.trial_data[self.block_countdown][self.current_trial]["start_time"] = time()
        self.trial_data[self.block_countdown][self.current_trial]["end_time"] = 0

        return self.current_trial

    def misclick(self):
        if self.trial_counter > 0:
            self.trial_data[self.block_countdown][self.current_trial]["errors"] = (
                                                                                      self.trial_data[
                                                                                          self.block_countdown][
                                                                                          self.current_trial][
                                                                                          "errors"]) + 1

    def setEndTime(self, end_time):
        if self.trial_counter > 0:
            self.trial_data[self.block_countdown][self.current_trial]["end_time"] = end_time
            self.trial_data[self.block_countdown]["block_end_time"] = time()

    def updateMouseLast(self, mouse_x, mouse_y):
        self.mouse_lastx = mouse_x
        self.mouse_lasty = mouse_y

    def trackMouseDistance(self, mouse_x, mouse_y):
        dist = self.distance([self.mouse_lastx, self.mouse_lasty], [mouse_x, mouse_y])
        self.trial_data[self.block_countdown][self.current_trial]["distance"] = \
            self.trial_data[self.block_countdown][self.current_trial]["distance"] + dist
        self.updateMouseLast(mouse_x, mouse_y)

    def printTrailData(self):
        for block in self.trial_data.keys():
            print("block: ", block)
            for trial in self.trial_data[block].keys():
                print("\t", trial, self.trial_data[block][trial])

    @staticmethod
    def distance(p0, p1):
        return sqrt((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2)


class MainCanvas:
    border_enter_color = "red"
    border_leave_color = "white"

    def __init__(self, root, canvas, color, width, height, participant_id):
        self.participant_id = participant_id
        self.app_root = root
        self.canvas = canvas
        self.id = canvas.create_rectangle(0, 0, width, height, fill=MainCanvas.border_leave_color, tags="background")
        self.canvas.bind('<Motion>', self.onMouseMove)
        self.width = width
        self.height = height

        self.text_id = self.canvas.create_text(width / 2 + 10, 20, anchor='se')
        self.canvas.itemconfig(self.text_id, text='', fill="blue")

        self.canvas.tag_bind("background", '<ButtonPress-1>', self.onBackgroundClick)
        self.canvas.tag_bind("circle", '<ButtonPress-1>', self.onCircleClick)

        self.canvas_item_to_object = dict()  # maps canvas object ids to the object they're linked to
        self.trial_tracker = Trials()  # create tracker to manage input data

        self.center_box = canvas.create_rectangle(width / 2 - 10, height / 2 - 10, width / 2 + 10, height / 2 + 10,
                                                  fill="orange", tags="center_box")
        self.canvas.tag_bind("center_box", '<ButtonPress-1>', self.onCenterBoxClick)

        self.task_was_reset = False  # flag to force people to click the center button to reset the task

    def onCenterBoxClick(self, event):
        # user clicked center box to get new task
        mouse_x, mouse_y = event.x, event.y
        if not self.task_was_reset:
            self.trial_tracker.setEndTime(time())
            next_trial = self.trial_tracker.getNextTrial()  # get the next trial
            if next_trial is not None:
                self.task_was_reset = True
                self.trial_tracker.updateMouseLast(mouse_x, mouse_y)
                direction_modifier = 1  # flips the direction of the circle right or left of center
                if next_trial[3] == "left":
                    direction_modifier = -1
                circle_radius = next_trial[1]
                circle_x = next_trial[2] * direction_modifier + (self.width / 2)
                circle_y = self.height / 2
                self.createCircle(circle_x, circle_y, circle_radius, "green")
            else:
                self.trial_tracker.printTrailData()  # report resules
                SQLHandler.insertTrialData(self.trial_tracker.trial_data, participant_id=self.participant_id)
                self.app_root.changePage(ThanksPage)  # experiment ended; switch to the thank you page


    def onMouseMove(self, event):
        mouse_x, mouse_y = event.x, event.y
        if self.task_was_reset:
            self.trial_tracker.trackMouseDistance(mouse_x, mouse_y)

    def onBackgroundClick(self, event):
        # user missed the button
        x, y = event.x, event.y
        self.trial_tracker.misclick()

    def onCircleClick(self, event):
        x, y = event.x, event.y
        # print('you clicked at {}, {}'.format(x, y))

        # get the item that was clicked and remove it
        if self.canvas.find_withtag(CURRENT):
            # print(self.canvas_item_to_object[self.canvas.find_withtag(CURRENT)[0]]) # get the actual circle linked to the canvas
            #Beep(400, 100)
            self.removeCircle(self.canvas.find_withtag(CURRENT)[0])
            self.task_was_reset = False
            self.updateProgressBar()

    def resetMousePosition(self):
        screen_x, screen_y = int(self.canvas.winfo_rootx()), int(self.canvas.winfo_rooty())
        #SetCursorPos(
        #    (int(screen_x + self.width / 2), int(screen_y + self.height / 2)))  # set cursor at center of canvas

    def updateProgressBar(self):
        self.canvas.itemconfig(self.text_id,
                               text=str(self.trial_tracker.trial_counter) + '/ ' + str(self.trial_tracker.trial_max),
                               fill="blue")

    def createCircle(self, x, y, radius, color):
        canvas_circle = self.canvas.create_oval(0, 0, radius * 2, radius * 2, fill=color, tags="circle")
        circle = Circle(self, self.canvas, canvas_circle)
        self.canvas.move(canvas_circle, x - radius, y - radius)  # starts at 0,0 so move it to new position
        self.canvas_item_to_object[canvas_circle] = circle

    def removeCircle(self, canvas_object):
        self.canvas.delete(canvas_object)
        self.canvas_item_to_object.pop(canvas_object)


class Circle:
    def __init__(self, parent, canvas, circle_id):
        self.parent = parent
        self.canvas = canvas
        self.circle_id = circle_id


class App(Tk):
    # manages pages and data across the app
    def __init__(self):
        Tk.__init__(self)
        self._frame = None
        self.configureApp()
        self.changePage(ConsentPage)

    def configureApp(self):
        self.attributes("-fullscreen", False)  # starts in windowed
        self.resizable(width=False, height=False)  # cannot resize window
        self.maxsize(1000, 800)
        self.title("Fitts' Law Experiment")

    def changePage(self, frame_class, participant_id=None):
        """Destroys current frame and replaces it with a new one."""
        if participant_id is not None:
            new_frame = frame_class(self, participant_id=participant_id)
        else:
            new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.grid()


class ConsentPage(Frame):
    def __init__(self, master=None):
        f = Frame.__init__(self, master)

        text = Label(self, text="You are requested to participate in this research study on target acquisition.\n"
                                "The study should take between 5 to 10 minutes to complete.\n"
                                "Participation is voluntary. You have the option to not respond to any question.\n"
                                "You may stop at any time. All information will remain anonymous.\n"
                                "If you are willing to consent and continue then click the 'I Consent' button.\n"
                                "If you do not consent, you may exit the window now."
                     )
        text.config(font=("Courier", 12))
        text.grid(row=0, column=0)

        self.columnconfigure(0, minsize=1000, weight=6)
        self.rowconfigure(0, minsize=600, weight=6)

        # change action of consent_button to collect participant data
        # Open a new window for participant to enter the demographic information
        # From there continue to Instruction Page
        #consent_button = Button(self, text="I Consent",
        #                        command=lambda: master.changePage(InstructionPage))
        consent_button = Button(self, text="I Consent",
                                command=lambda : master.changePage(DemographicsPage))

        consent_button.grid(row=1, column=0)
        self.rowconfigure(1, minsize=100, weight=6)


class DemographicsPage(Frame):
    def __init__(self, master=None):
        f = Frame.__init__(self, master)

        text = Label(self, text="Demographic Data to be collected here")
        # IDEA:
        # Collect each item for demographic data
        # Create an instance of Participant
        # WITH USER INPUT HERE BEFORE SENDING TO DB
        participant = Participant()   # add form stuff before this step

        participant_id = SQLHandler.addUser(participant)

        text.config(font=("Courier", 12))
        text.grid(row=0, column=0)

        self.columnconfigure(0, minsize=1000, weight=6)
        self.rowconfigure(0, minsize=600, weight=6)

        # change action of consent_button to collect participant data
        # Open a new window for participant to enter the demographic information
        # From there continue to Instruction Page
        consent_button = Button(self, text="I Consent",
                                command=lambda: master.changePage(InstructionPage, participant_id=participant_id))

        consent_button.grid(row=1, column=0)
        self.rowconfigure(1, minsize=100, weight=6)



class InstructionPage(Frame):
    def __init__(self, master=None, participant_id=None):
        f = Frame.__init__(self, master)

        text = Label(self, text="Instructions\n\n\n"
                                "Click the orange square to begin each task.\n"
                                "A green circle will appear. Your goal is to click the green circle as quickly as possible.\n"
                                "You also want to have the smallest number of errors as possible. \n"
                                "An error is a click that misses the green circle.\n"
                                "Please click the orange square to start the next task.\n"
                                "There are a total of 320 tasks. Your progress will be visible the top of the screen."
                     )
        text.config(font=("Courier", 12))
        text.grid(row=0, column=0)

        self.columnconfigure(0, minsize=1000, weight=6)
        self.rowconfigure(0, minsize=600, weight=6)

        begin_button = Button(self, text="Begin trials",
                              command=lambda: master.changePage(ApplicationPage, participant_id))

        begin_button.grid(row=1, column=0)
        self.rowconfigure(1, minsize=100, weight=6)


class ApplicationPage(Frame):
    def __init__(self, master=None, participant_id=None):
        Frame.__init__(self, master)
        self.grid()
        self.elements = dict()  # create a dictionary that houses all the objects, so you can reference them in other methods

        # configure all the rows and columns to have default weights (z-index)
        for r in range(1):  # height in rows
            self.rowconfigure(r, weight=1)
        for c in range(1):  # width in columns
            self.columnconfigure(c, weight=1)

        ########### main canvas for graph rendering
        # make a frame to house the main canvas. The frame adheres to the grid scheme but the canvas is packed
        self.elements["main_canvas_background"] = Frame(self, bg="grey")
        self.elements["main_canvas_background"].grid(row=0, column=0, rowspan=1, columnspan=1, sticky=N + W + S + E)
        self.columnconfigure(0, minsize=1000, weight=6)
        self.rowconfigure(0, minsize=100, weight=6)

        # main canvas
        self.elements["main_canvas"] = Canvas(self.elements["main_canvas_background"], width=1000, height=700, bd=0,
                                              highlightthickness=0)
        self.elements["main_canvas"].pack()

        self.border = MainCanvas(master, self.elements["main_canvas"], "white", 1000, 700, participant_id)


class ThanksPage(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.grid()

        text = Label(master, text="Thank you for participating in this study")
        text.config(font=("Courier", 12))
        text.grid(row=0, column=0)

        self.columnconfigure(0, minsize=1000, weight=6)
        self.rowconfigure(0, minsize=600, weight=6)

        consent_button = Button(self, text="close", command=quit)

        consent_button.grid(row=1, column=0)
        self.rowconfigure(1, minsize=100, weight=6)


if __name__ == "__main__":
    app = App()
    app.mainloop()
