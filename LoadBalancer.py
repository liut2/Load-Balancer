import sys
import socket
import select
import random
from itertools import cycle

#we define the server pool of three servers on the localhost, 
#at the port number of 7777, 8888 and 9999
SERVER_POOL = [("localhost", 7777), ("localhost", 8888), ("localhost", 9999)]
ITER = cycle(SERVER_POOL)

def round_robin(iter):
	return next(iter)

class LoadBalancer(object):
	sockets = list()
	flow_table = dict()
	#init methods
	#to the outside world, the load balancer acts as a virtual server, so we need to have the 
	#ip and port info of this virtual server to create sockets that is able to do end-to-end
	#communication from the between the client and the virtual server
	def __init__(self, ip, port, algorithm):
		self.ip = ip
		self.port = port
		self.algorithm = algorithm
		#init the virtual_server_socket which listens to client request
		#we define it as a socket communicating between machines in the network and based on
		#TCP transmission
		self.virtual_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		#we reuse this socket
		self.virtual_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		#we bind the socket to its server port for listening later
		self.virtual_server_socket.bind((self.ip, self.port))
		#this means at most we can listen to ten client request standing in a queue waiting to be accpted
		#after this number, the socket stops listening
		print 'init virtual server socket: %s' % (self.virtual_server_socket.getsockname(),)
		self.virtual_server_socket.listen(10)
		
		self.sockets.append(self.virtual_server_socket)

	def start(self):
		#we endlessly listen to the client request
		while True:
			#we use the non-blocking select methods to pick out those active connections
			read_list, write_list, exception_list = select.select(self.sockets, [], [])
			for socket in read_list:
				if socket == self.virtual_server_socket:
					print '='*40+'flow start'+'='*39
					#if we iterate to the virtual_server_socket, then we can begin the listen mode
					self.on_accept()
					break
				else:
					try: 
						#if the socket is not the virtual_server_socket, then it is the newly created
						#connection after the virtual_server_socket accepts and the new socket obejct
						#being returned on server side

						#this is blocking receive in that we need to get every complete 1024 bytes
						#before the data is returned, but if we don't specify the number, then it's a 
						#non-blocking one, we return any data received
						data = socket.recv(4096)
						if data:
							#if we haven't received data, then we prepare to receive more
							self.on_receive(socket, data)
							#break
						else:
							#if no more data available, then we close the socket
							self.on_close(socket)
							break
					except:
						self.on_close(socket)
						break

	def on_accept(self):
		#when on _accept, the virutal_server_socket enters the waiting mode and block communication
		#until it receives a connecting request. now it returns a new socket object which will be responsible 
		#for sending and receiving msg from client in the future, and our original virtual_server_socket returns to 
		#its job of listening
		connection, client_address = self.virtual_server_socket.accept()
		print 'client connected: %s <==> %s' % (client_address, self.virtual_server_socket.getsockname())
		#after virtual_server_socket accepts the connection request, we now init the virtual_client_socket
		#which is then responsible for sending the data(request) to the real servers behind the scenes
		real_server_ip, real_server_port = self.select_server(SERVER_POOL, self.algorithm)
		print "real server ip is " + str(real_server_ip) + " " + str(real_server_port)
		virtual_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			virtual_client_socket.connect((real_server_ip, real_server_port))
			print 'init virtual_client_socket : %s' % (virtual_client_socket.getsockname(),)
			print 'server connected: %s <==> %s' \
                   % (virtual_client_socket.getsockname(),(socket.gethostbyname(real_server_ip), real_server_port))
		except:
			print "Can't establish connection with remote server, err: %s" % sys.exc_info()[0]
			print "Closing connection with client socket %s" % (client_address,)
			connection.close()
			return
		#we now add the mapping to the flow_table so when the tranmission really starts, the virtual
		#server_socket and virtual_client_socket can know each other

		self.sockets.append(connection)
		self.sockets.append(virtual_client_socket)

		self.flow_table[connection] = virtual_client_socket
		self.flow_table[virtual_client_socket] = connection

		

	def on_receive(self, socket, data):
		#after the new connection get the data from the client, then we send the data to the real 
		#servers behind the scenes
		#actually this is bi-direction transmission, if the socket stands for the connection socket, we then find its corresponding virtual-client socket to send the data to the real server; if the socket stands for the virtual client socket, then we find its corresponding connection socket, and then send the data to back to client
		print 'recving packets: %-20s ==> %-20s, data: %s' \
               % (socket.getpeername(), socket.getsockname(), [data])
		virtual_client_socket = self.flow_table[socket]
		virtual_client_socket.send(data)
		print 'sending packets: %-20s ==> %-20s, data: %s' \
               % (virtual_client_socket.getsockname(), virtual_client_socket.getpeername(), [data])

	def on_close(self, socket):
		virtual_client_socket = self.flow_table[socket]
		#now the connection is not active anymore, so we remove it from the task queue
		self.sockets.remove(socket)
		self.sockets.remove(virtual_client_socket)
		#we close the communication between the client and the virtual_server_socket
		#we also close the communication between the virutal_client_socket and the real server
		socket.close()
		virtual_client_socket.close()

		del self.flow_table[socket]
		del self.flow_table[virtual_client_socket]

	def select_server(self, server_pool, algorithm):
		if algorithm == "round_robin":
			return round_robin(ITER)
		elif algorithm == "random":
			return random.choice(server_pool)
		

if __name__ == "__main__":
	LoadBalancer("localhost", 5555, "round_robin").start()




