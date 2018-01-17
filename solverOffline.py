import sys
from random import *
import signal
import sqlite3
from datetime import date, datetime
import wx
import wx.lib.mixins.inspection as WIT
import matplotlib
from numpy import arange, sin, pi


matplotlib.use('WX')
from matplotlib.backends.backend_wx import FigureCanvasWx as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

from matplotlib.figure import Figure

conn = sqlite3.connect("tsp.db")
c = conn.cursor()


def addProblem(path):
	with open(path) as f:
	    content = f.read().splitlines()
	count = 0
	while content[count] not in 'NODE_COORD_SECTION:':
		if content[count].split()[0] in 'NAME:':
			name = content[count].split()[len(content[count].split())-1]
		elif content[count].split()[0] in 'COMMENT:':
			comment = content[count].split()[len(content[count].split())-1]
		elif content[count].split()[0] in 'TYPE:':
			if content[count].split()[len(content[count].split())-1] != 'TSP':
				print('type not tsp')
				exit()
		elif content[count].split()[0] in 'DIMENSION:':
			dimentions = int(content[count].split()[len(content[count].split())-1])
		elif content[count].split()[0] in 'EDGE_WEIGHT_TYPE:':
			if content[count].split()[len(content[count].split())-1] != 'EUC_2D':
				print('type not EUC_2D')
				exit()
		count+=1
	count+=1
	inserting = (name, dimentions, comment)
	c.execute("INSERT INTO Problem VALUES (?,?,?)", inserting)
	while content[count] not in 'EOF':
		inserting = (name, content[count].split()[0], content[count].split()[1], content[count].split()[2])
		c.execute("INSERT INTO Cities VALUES (?,?,?,?)", inserting)
		count+=1
	conn.commit()

def allProblems():
	c.execute("SELECT Name FROM Problem")
	tempList = []
	for i in c.fetchall():
		tempList.append(i[0])
	return tempList

def allSolutionsText(problem):
	checkProb = (problem, )
	c.execute("SELECT Author, TourLength FROM Solution WHERE ProblemName=?", checkProb)
	tempList = []
	for i in c.fetchall():
		tempList.append(str(i[0]) + " | " + str(i[1]))
	return tempList

def allSolutionsSelect(problem):
	checkProb = (problem, )
	c.execute("SELECT SolutionID FROM Solution WHERE ProblemName=?", checkProb)
	tempList = []
	for i in c.fetchall():
		tempList.append(i[0])
	return tempList

def getPoints(solutionID):
	sol = (solutionID,)
	c.execute("SELECT ProblemName, Tour FROM Solution WHERE SolutionID=?", sol)
	the_sollution = list(c.fetchone())
	cityName = (the_sollution[0],)
	c.execute("SELECT * FROM Cities WHERE Name=?", cityName)
	dimentions = len(c.fetchall())
	c.execute("SELECT * FROM Cities WHERE Name=?", cityName)
	arr = [0 for i in range(dimentions)]
	for i in range(dimentions):
		name, ID, ourX, ourY = c.fetchone()
		arr[i] = float(ourX), float(ourY), int(ID)
	final_sol = [0 for i in range(dimentions)]
	for i in range(dimentions):
		for j in range(len(arr)):
			if int(the_sollution[1].split()[i]) == int(arr[j][2]):
				final_sol[i] = arr.pop(j)
				break
	return final_sol

def getPointsOfProblem(problem):
	cityName = (problem,)
	c.execute("SELECT * FROM Cities WHERE Name=?", cityName)
	dimentions = len(c.fetchall())
	c.execute("SELECT * FROM Cities WHERE Name=?", cityName)
	arr = [0 for i in range(dimentions)]
	for i in range(dimentions):
		name, ID, ourX, ourY = c.fetchone()
		arr[i] = float(ourX), float(ourY), int(ID)
	return arr



def solveFull(passed_name, takeTime):
	gene_pool_size = 30
	time_in_seconds = int(takeTime)
	name = (passed_name,)
	c.execute("SELECT * FROM Cities WHERE Name=?", name)
	dimentions = len(c.fetchall())
	c.execute("SELECT * FROM Cities WHERE Name=?", name)
	arr = [0 for i in range(dimentions)]
	fitness = [0 for i in range(gene_pool_size)]
	current_gene_pool = [[0 for i in range(dimentions)]for j in range(gene_pool_size)]
	new_gene_pool = [[0 for i in range(dimentions)]for j in range(gene_pool_size)]

	#functions#

	def cross_segment(p, q, r):
		if ((q[0]<=max(p[0], r[0])) and
			(q[0]>=min(p[0], r[0])) and
			(q[1]<=max(p[1], r[1])) and
			q[1] >= min(p[1, r[1]])):
			return 0
		return 1

	def orientation(p, q, r):
		val = (q[1]-p[1])*(r[0]-q[0])-(q[0]-p[0])*(r[1]-q[1])
		if(val == 0):
			return 0
		return 1 if val>0 else 2

	def do_intersect(p1, q1, p2, q2):
		o1 = orientation(p1, q1, p2)
		o2 = orientation(p1, q1, q2)
		o3 = orientation(p2, q2, p1)
		o4 = orientation(p2, q2, q1)
		if o1!=o2 and o3!=o4:
			return 1
		return 0

	def ucl_dist(a, b):
		return ((abs(a[0]-b[0]))**2+(abs(a[1]-b[1]))**2)**0.5

	def closest_neigbour(from_place, city_list):
		lowest = ucl_dist(from_place, city_list[0])
		place = 0
		for i in range(len(city_list)-1):
			if ucl_dist(from_place, city_list[i+1]) < lowest:
				lowest = ucl_dist(from_place, city_list[i+1])
				place = i+1
		return place

	#x is gene pool
	def make_first_gen(x):
		temp_arr = list(arr)
		j = 0
		current_gene_pool[0][j] = tuple(temp_arr.pop(j))
		while temp_arr:
			j+=1
			current_gene_pool[0][j] = tuple(temp_arr.pop(closest_neigbour(current_gene_pool[0][j-1], temp_arr)))
		for i in range(x-1):
			current_gene_pool[i+1] = list(current_gene_pool[i])
			mutator(current_gene_pool[i+1], 100)
		return current_gene_pool

	def check_total_distance(rout):
		distance = 0
		for i in range(len(rout)-2):
			distance+=ucl_dist(rout[i], rout[i+1])
		distance+=ucl_dist(rout[0], rout[len(rout)-1])
		return distance

	def crossed(rout):
		interected = 0
		for i in range(len(rout)-4):
			for j in range(i):
				if do_intersect(rout[j], rout[j+1], rout[i+3], rout[i+4]):
					interected += 1
		return interected

	def fitness_generator(gene_pool):
		for i in range(len(gene_pool)):
			temp = check_total_distance(gene_pool[i])
			fitness[i] = temp+crossed(gene_pool[i])/temp
		return fitness

	def roulette_wheel_selection(fitness):
		total = 0
		for i in range(len(fitness)):
			total += fitness[i]
		our_selection = random()*total
		for i in range(len(fitness)):
			if our_selection>=total:
				return i
			total -= fitness[i]
		return roulette_wheel_selection(fitness)

	def mutator(specimen, x):
		gene_being_held = 0
		for i in range(len(specimen)):
			if randint(0, x) == 5:
				if gene_being_held:
					gene_holder = tuple(specimen[i])
					specimen[i] = tuple(specimen[gene_hold_n])
					specimen[gene_hold_n] = tuple(gene_holder)
				else:
					gene_hold_n = i

	def next_gen(gene_pool):
		max = float('-inf');
		min = float('inf');
		for i in fitness:
			if(i < min):
				min = i;
			if(i > max):
				max = i;
		for i in range(0, len(fitness)):
			fitness[i] = ((max-min)-(max-fitness[i]))**2
		for i in range(len(gene_pool)):
			parent1 = list(gene_pool[roulette_wheel_selection(fitness)])
			parent2 = list(gene_pool[roulette_wheel_selection(fitness)])
			splitage_value = int(gauss(int(dimentions/2), int((dimentions/20))))
			for j in range(splitage_value):
				new_gene_pool[i][j] = tuple(parent1[j])
				for k in range(len(parent2)):
					if parent1[j][2] == parent2[k][2]:
						parent2.pop(k)
						break
			for j in range(len(parent2)):
				new_gene_pool[i][j+splitage_value] = tuple(parent2[j])
			mutator(new_gene_pool[i], 1000)
		return new_gene_pool

	def output(gene_pool):
		length = 0.0
		for i in range(len(gene_pool)):
			if not length or check_total_distance(gene_pool[i]) < length:
				length = check_total_distance(gene_pool[i])
				best_tour = i
		winner=""
		for i in range(len(gene_pool[best_tour])):
			winner += str(gene_pool[best_tour][i][2]) + ' '
		winner += '-1'
		inserting = (name, int(length), datetime.now(), 5027271, "Greedy+Genetic+2opt", time_in_seconds, winner)
		return inserting

	class TimeoutException(Exception):   # Custom exception class
		pass

	def timeout_handler(signum, frame):   # Custom signal handler
		raise TimeoutException

	# Change the behavior of SIGALRM
	signal.signal(signal.SIGALRM, timeout_handler)


	#main code#
	#populating main data
	for i in range(dimentions):
		name, ID, ourX, ourY = c.fetchone()
		arr[i] = float(ourX), float(ourY), int(ID)

	#free memory
	content = 0

	fitness_generator(make_first_gen(gene_pool_size))
	signal.alarm(time_in_seconds)
	try:
		while 1:
			current_gene_pool = list(next_gen(current_gene_pool))
			fitness_generator(current_gene_pool)
	except TimeoutException:
		c.execute("INSERT INTO Solution VALUES (null,?,?,?,?,?,?,?)", output(current_gene_pool))
		conn.commit()
		length = 0.0
		for i in range(len(current_gene_pool)):
			if not length or check_total_distance(current_gene_pool[i]) < length:
				length = check_total_distance(current_gene_pool[i])
				best_tour = i
		return current_gene_pool[best_tour]

	else:
		signal.alarm(0)


class myGui(wx.Frame):
	def __init__(self,parent,id,title):
		wx.Frame.__init__(self,parent,id,title)
		self.parent = parent
		self.initialise()
		pnl = wx.Panel(self)

		self.sizer = wx.GridBagSizer(hgap=5, vgap=5)

		#canvas
		self.figure = Figure()
		self.canvas = FigureCanvas(self, -1, self.figure)
		self.sizer.Add(self.canvas, pos = (0, 1), span = (4, 1), flag = wx.EXPAND)

		fileMenu = wx.Menu()
		loadFile = fileMenu.Append(wx.ID_OPEN)
		exitItem = fileMenu.Append(wx.ID_EXIT)


		helpMenu = wx.Menu()
		aboutItem = helpMenu.Append(wx.ID_ABOUT)

		self.problems = wx.Choice(pnl,choices = allProblems())
		self.problems.Bind(wx.EVT_CHOICE, self.Problems)
		self.sizer.Add(self.problems, pos = (0, 0), span = (1, 1), flag = wx.EXPAND)

		self.solutions = wx.Choice(pnl,choices = allSolutionsText(allProblems()[self.problems.GetSelection()]))
		self.solutions.Bind(wx.EVT_CHOICE, self.Solutions)
		self.sizer.Add(self.solutions, pos = (1, 0), span = (1, 1), flag = wx.EXPAND)

		solve = wx.Button(pnl, label="SOLVE")
		self.Bind(wx.EVT_BUTTON, self.Solve, solve)
		self.sizer.Add(solve, pos = (2, 0), span = (1, 1), flag = wx.EXPAND)

		menuBar = wx.MenuBar()
		menuBar.Append(fileMenu, "&File")
		menuBar.Append(helpMenu, "&Help")

		self.SetMenuBar(menuBar)

		self.Bind(wx.EVT_MENU, self.OnExit,  exitItem)
		self.Bind(wx.EVT_MENU, self.OnAbout, aboutItem)
		self.Bind(wx.EVT_MENU, self.loadFile, loadFile)

		self.dlg = wx.TextEntryDialog(pnl, 'Enter the amount of seconds you want to run solver for:','Time')

		pnl.SetSizerAndFit(self.sizer)
		self.SetSizerAndFit(self.sizer)

	def initialise(self):
		self.Show(True)

	def OnExit(self, event):
		conn.close()
		self.Close(True)

	def OnAbout(self, event):
		wx.MessageBox("s5027271 Bachlor of Computer Science 2017 \n\n                       Grifith Univerity",
		"Made By Thomas Csere", 				                     wx.OK | wx.ICON_INFORMATION)

	def loadFile(self, event):
		openFileDialog = wx.FileDialog(self, "Open", "", "",
										"Traveling Salesman Problem (*.tsp)|*.tsp",
										wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		openFileDialog.ShowModal()
		addProblem(openFileDialog.GetPath())
		wx.MessageBox("Problem Added")
		openFileDialog.Destroy()

	def Problems(self,event):
		self.solutions.Clear()
		self.solutions.AppendItems(allSolutionsText(allProblems()[self.problems.GetSelection()]))
		self.axes = self.figure.add_subplot(111)
		self.axes.clear()
		sol = getPointsOfProblem(allProblems()[self.problems.GetSelection()])
		x = []
		for i in range(len(sol)):
			x.append(sol[i][0])
		x.append(x[0])
		y = []
		for i in range(len(sol)):
			y.append(sol[i][1])
		y.append(y[0])

		self.axes.plot(x, y, 'o')

		self.SetSizerAndFit(self.sizer)


	def Solutions(self,event):
		sol = getPoints(allSolutionsSelect(str(allProblems()[self.problems.GetSelection()]))[self.solutions.GetSelection()])
		self.axes.clear()
		x = []
		for i in range(len(sol)):
			x.append(sol[i][0])
		x.append(x[0])
		y = []
		for i in range(len(sol)):
			y.append(sol[i][1])
		y.append(y[0])

		self.axes.plot(x, y)
		self.SetSizerAndFit(self.sizer)

	def Solve(self,event):
		if(self.problems.GetSelection()>=0):
			self.dlg.ShowModal()
			if(int(self.dlg.GetValue()) >= 0):
				sol = solveFull(str(allProblems()[self.problems.GetSelection()]), self.dlg.GetValue())
				self.axes.clear()
				x = []
				for i in range(len(sol)):
					x.append(sol[i][0])
				x.append(x[0])
				y = []
				for i in range(len(sol)):
					y.append(sol[i][1])
				y.append(y[0])

				self.axes.plot(x, y)
				self.SetSizerAndFit(self.sizer)
				wx.MessageBox("Probem Solved")







app = wx.App()
frame = myGui(None,-1,"My Application")
app.MainLoop()


# elif sys.argv[2] == "FETCH":
# 	name = (sys.argv[1],)
# 	c.execute("SELECT Solution FROM Solutions WHERE PName=? ORDER BY Size ASC", name)
# 	content = c.fetchone()
# 	print(content)
