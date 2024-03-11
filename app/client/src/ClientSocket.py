import socket
import pickle
import threading
from Packet import Packet


class ClientSocket:
    def __init__(self, host='127.0.0.1', port=3000, listening=True):
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_client.connect((host, port))
        self.listening = listening
        self.id = None
        self.player_data = None
        self.round_data = [90,"map_1"]
        return
    
    def start_thread(self):
        self.socket_thread = threading.Thread(target=self.socket_receive_data)
        self.socket_thread.start()

    def kill_connection(self):
        self.listening = False
        self.socket_client.close()

    def send_data(self,msg,content=None):
        data = Packet(source=self.id, header=msg, data=content)
        data = data.serialize()
        self.socket_client.send(data)
        pass

    def socket_receive_data(self):
        while True:
            response = self.socket_client.recv(4096)
            response = self.unpack_packet(response)
            
            
            if False:
                print("{")
                print(f"source:{response.source},")
                print(f"header:{response.header},")
                print(f"data:{response.data},")
                print("}")
        
            if(response.header == "connected"):
                self.id = response.data
            elif(response.header == "kill-socket" or response.header == "lobby-full"):
                print("Im DEAD")
                break      
            elif(response.header == "server-message"):
                print("----SERVER MESSAGE----")
                print(f"  {response.data}    ")
                print("----------------------")
            elif(response.header == "player-tick"):
                self.player_data = response.data
            elif(response.header == "update-tick"):
                self.round_data = response.data

        self.kill_connection()
        return 

    def unpack_packet(self, data):
        return pickle.loads(data)