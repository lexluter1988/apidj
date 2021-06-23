import argparse
import logging

from pylxd import Client
from pylxd.exceptions import NotFound


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Config:
    "that would be store for all properties we need"

    endpoint = 'https://172.29.232.11:8443'
    
    key = 'lxd.key'
    cert = 'lxd.crt'

    image_servers = [
        'https://images.linuxcontainers.org',
        'https://cloud-images.ubuntu.com/releases',
        'https://cloud-images.ubuntu.com/daily']


class LxdAdapter:
    def __init__(self) -> None:
        self.client = Client(
            endpoint=Config.endpoint, 
            cert=(Config.cert, Config.key), 
            verify=False)

    def create_container(self, name, os='ubuntu/21.04'):
        config = {
            'name': name, 
            'source': {
                'type': 'image', 
                "mode": 'pull', 
                'server': Config.image_servers[0], 
                'protocol': 'simplestreams', 
                'alias': os},
            'profiles': ['default'] 
            }

        # checking for existing container
        try:
            i = self.client.instances.get(name)
            logger.error('Container {} already exists, please chose another name'.format(name))
            raise
            #i.delete()
        except NotFound:
            logger.info('Container {} not found, can be created'.format(name))

        try:
            instance = self.client.instances.create(config, wait=True)
            instance.start(wait=True)
            from time import sleep
            sleep(1)
        except Exception as e:
            logger.error('Unhandled exception {}'.format(e))
            raise
        
        logger.info('Created container: {} with IP: {}'.format(name, instance.state().network['eth0']['addresses'][0]['address']))
        return instance

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, help="Name of the container to create", required=True)
    name = parser.parse_args().name
    
    lxd = LxdAdapter()
    lxd.create_container(name)

if __name__ == '__main__':
    main()


#TODO

#out = i.execute(['apt', 'install', 'postgresql', '-y'])
#print(out.stdout)
#instance.start(wait=False)
# django routine
#instance.execute(['apt', 'install', 'postgresql', '-y'])
#instance.execute(['apt', 'install', '-y', 'python3-pip', 'python3-dev', 'libpq-dev', 'postgresql', 'postgresql-contrib', 'nginx', 'curl'])
# end
