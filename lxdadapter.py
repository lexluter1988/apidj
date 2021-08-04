import argparse
import logging
from abc import ABCMeta, abstractmethod
from uuid import uuid4

from pylxd import Client
from pylxd.exceptions import NotFound
from pylxd.models import Instance, Container

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Result:
    def __init__(self, status=None) -> None:
        self.status = status


class AbstractOperation:
    __metaclass__ = ABCMeta

    version = '0.1'

    @abstractmethod
    def __init__(self, operation, args):
        self.operation = operation
        self.args = args

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def _on_success(self):
        pass

    @abstractmethod
    def _on_failure(self):
        pass

    def __repr__(self) -> str:
        return f"Operation: {self.operation}"


class DeleteContainerOperation(AbstractOperation):

    def __init__(self, operation, args) -> None:
        super().__init__(operation, args)
        self.name = 'DeleteContainer'
        self.operation = operation
        self.args = args

    def execute(self):
        # TODO: better logging for every execution
        result = Result('success')
        try:
            self.operation(self.args)
        except:
            result.status = 'failed'
            self._on_failure()
        self._on_success()
        return result


class FindContainerOperation(AbstractOperation):

    def __init__(self, operation, args) -> None:
        super().__init__(operation, args)
        self.name = 'FindContainer'
        self.operation = operation
        self.args = args

    def execute(self):
        result = Result('success')
        try:
            self.operation(self.args)
        except:
            result.status = 'failed'
            self._on_failure()
        self._on_success()
        return result


class CreateContainerOperation(AbstractOperation):

    def __init__(self, operation, args) -> None:
        super().__init__(operation, args)
        self.name = 'CreateContainer'
        self.operation = operation
        self.args = args

    def execute(self):
        result = Result('success')
        try:
            self.operation(**self.args)
        except:
            result.status = 'failed'
            self._on_failure()
        self._on_success()
        return result


class EchoOperation(AbstractOperation):
    def __init__(self, args, operation='echo') -> None:
        super().__init__(operation, args)
        self.name = 'Echo'
        self.args = args

    def execute(self):
        result = Result('success')
        try:
            print(self.args)
        except:
            result.status = 'failed'
            self._on_failure()
        self._on_success()
        return result


class Pipeline:
    def __init__(self) -> None:
        self.operations = []

    def add(self, step):
        self.operations.append(step)
        return self

    def run_async(self):
        pass

    def run(self):
        for step in self.operations:
            result = step.execute()
            if result.status == 'failed':
                logger.error('We should not continue, pipeline should fall')
                raise Exception("ARRRHHHH!!!")
            else:
                logger.info('All good with that one, lets do the next operation')

    def __repr__(self) -> str:
        return f"Pipeline with: {[operation.name for operation in self.operations]}"


class Config:
    "that would be store for all properties we need"

    endpoint = 'https://10.211.55.6:8443'

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

    def delete_container(self, name):
        try:
            print('getting container')
            i = self.client.instances.get(name)
            print('stopping container')
            i.stop(name, wait=True)
            print('deleting container')
            i.delete(name, wait=True)
            logger.info('Container {} has been deleted'.format(name))
        except NotFound:
            logger.error('Container {} deletion failed'.format(name))

    def find_container(self, name):
        try:
            self.client.instances.get(name)
            logger.info('Container {} already exists'.format(name))
        except NotFound:
            logger.error('Container {} not found'.format(name))

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
            self.client.instances.get(name)
            logger.error('Container {} already exists, please chose another name'.format(name))
            raise
        except NotFound:
            logger.info('Container {} not found, can be created'.format(name))

        try:
            # TODO this is why I cannot get operation after creation, it's inside of pylxd
            # response = client.api[cls._endpoint].post(json=config, target=target)

            # if wait:
            #     client.operations.wait_for_operation(response.json()["operation"])
            # return cls(client, name=config["name"])

            instance = self.client.instances.create(config, wait=True)
            instance.start(wait=True)
            from time import sleep
            sleep(1)
        except Exception as e:
            logger.error('Unhandled exception {}'.format(e))
            raise

        logger.info('Created container: {} with IP: {}'.format(name, instance.state().network['eth0']['addresses'][0][
            'address']))
        return instance


class CreateContainerPipeline(Pipeline):
    def __init__(self, context):
        super().__init__()
        self.operations = [
            EchoOperation("begin"),
            EchoOperation("test connection"),
            CreateContainerOperation(
                getattr(context.client, context.operation),
                {'name': context.args, 'os': 'ubuntu/21.04'}),
            EchoOperation("finished")
        ]


class FindContainerPipeline(Pipeline):
    def __init__(self, context):
        super().__init__()
        self.operations = [
            EchoOperation("begin"),
            EchoOperation("test connection"),
            # IDK if we really need to extract operation from context, cause we know what is FindContainerOperation
            FindContainerOperation(getattr(context.client, context.operation), context.args),
            EchoOperation("finished")
        ]


class DeleteContainerPipeline(Pipeline):
    def __init__(self, context):
        super().__init__()
        self.operations = [
            EchoOperation("begin"),
            EchoOperation("test connection"),
            DeleteContainerOperation(getattr(context.client, context.operation), context.args),
            EchoOperation("finished")
        ]


class Context:
    def __init__(self, client, operation, args):
        self.uuid = uuid4()
        self.client = client
        self.operation = operation
        self.args = args
        self.result = None

    @classmethod
    def make_context(cls, operation, args):
        # TODO: this is really consuming operation
        # every init will trigger connection attempt
        return cls(LxdAdapter(), operation, args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, help="Name of the container to create", required=True)
    parser.add_argument("--action", type=str, help="Action you want to do", required=True)
    name = parser.parse_args().name
    action = parser.parse_args().action
    context = Context.make_context(action, name)
    if 'create' in action:
        pipeline = CreateContainerPipeline(context)
    elif 'find' in action:
        pipeline = FindContainerPipeline(context)
    elif 'delete' in action:
        pipeline = DeleteContainerPipeline(context)
    else:
        raise Exception("Please chose wisely")

    # lxd = LxdAdapter()
    # pipeline = Pipeline()
    # pipeline.add(EchoOperation("begin"))
    # pipeline.add(EchoOperation("test connection"))
    # pipeline.add(CreateContainerOperation(lxd.create_container, {'name': name, 'os': 'ubuntu/21.04'}))
    # pipeline.add(FindContainerOperation(lxd.find_container, name))
    # pipeline.add(EchoOperation("finished"))

    pipeline.run()

    # lxd.create_container(name)


if __name__ == '__main__':
    main()

# TODO

# out = i.execute(['apt', 'install', 'postgresql', '-y'])
# print(out.stdout)
# instance.start(wait=False)
# django routine
# instance.execute(['apt', 'install', 'postgresql', '-y'])
# instance.execute(['apt', 'install', '-y', 'python3-pip', 'python3-dev', 'libpq-dev', 'postgresql', 'postgresql-contrib', 'nginx', 'curl'])
# end

# one line config
# config = {'name': 'ubuntu', 'source': {'type': 'image', 'mode': 'pull', 'server': Config.image_servers[0], 'protocol': 'simplestreams', 'alias': 'ubuntu/21.04'}, 'profiles': ['default'] }
