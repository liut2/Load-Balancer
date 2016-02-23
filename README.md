# Load-Balancer
## Brief Introduction
This is a simple single-thread load balancer implemented through python socket programming. The program manages the load balancing tasks from client requests through two types of algorithms:
* round-robin, which distributes the client request evenly to every server in a circular behavior
* randomized, which hashes the request code to distribute them randomly onto certain server

This program manages the bidirection communcation with the concept of a flow table:
* when there is client request sent to the server, the virtual server on load balancer listens and accepts the request by returning a sentinel connection socket
* then the program establishes the communication path through client -> -virtual server -> virtual client -> real server, by storing the correspondence of the virtual server and virtual client in a dictionary called flow table
* then later when the socket receives data, it find its corresponding path in the flow table, and send the data to its final destination
