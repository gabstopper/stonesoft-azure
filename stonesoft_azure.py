"""
Fully provision a Stonesoft NGFW into Microsoft Azure.

The NGFW is created within a resource group which will be created with a 
custom tag of 'stonesoft' so it can be searched after by using the ``list``
argument.
"""
import os
import json
import logging
import argparse
from azure.common.credentials import UserPassCredentials, ServicePrincipalCredentials
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.resource.resources.models import DeploymentMode
from smc import session
from smc.core.engines import Layer3Firewall
from smc.elements.helpers import location_helper
from smc.elements.network import Network
from msrestazure.azure_exceptions import CloudError
from smc.policy.layer3 import FirewallPolicy
from smc.api.exceptions import ElementNotFound, DeleteElementFailed
from azure.mgmt.resource.resources.v2017_05_10.models.template_link import TemplateLink
from azure.mgmt.resource.subscriptions.v2016_06_01.subscription_client import SubscriptionClient

logger = logging.getLogger(__name__)
    
# This script expects that the following settings are in place:

# If using Service Credentials:
# AZURE_TENANT_ID: with your Azure Active Directory tenant id or domain
# AZURE_CLIENT_ID: with your Azure Active Directory Application Client ID
# AZURE_CLIENT_SECRET: with your Azure Active Directory Application Secret

# If using user credentials:            
# export AZURE_USERNAME={my_username}
# export AZURE_PASSWORD={my_password}
# export AZURE_SUBSCRIPTION_ID={subscription_id}

# Note: Service credentials are attempted first.

# For the SMC Credentials, set the following environment variables:
# export SMC_API_KEY={key_generated_for_my_api_client}
# export SMC_ADDRESS={http://10.10.10.10}

# You have an SSH public key stored in '~/.ssh/id_rsa.pub'

# Deploy from a local template:
# (venv351) python stonesoft_azure.py create \
#    --engine_username dlepage \
#    --resource_group dlepage-rg \
#    --engine_location='Internet' \
#    --template_path=templates/engine.json \
#    --location_id westeurope \
#    --force_remove

# Deploy from a github based template with extra options:
# (venv351) python stonesoft_azure.py create \
#    --engine_username dlepage \
#    --resource_group dlepage-rg \
#    --engine_location='Internet' \
#    --template_link=https://raw.githubusercontent.com/gabstopper/stonesoft-cloud/master/azuredeploy.json \
#    --location_id westeurope \
#    --tag_value 'my custom value'
#    --force_remove

# List examples
# python stonesoft_azure.py list --by_tag stonesoft
# python stonesoft_azure.py list --all
# python stonesoft_azure.py list --resources_by_group {myresourcegroup}


subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID', '') 


def provision_stonesoft(name, vnet=None, location=None):
    """
    Create stonesoft firewall
    """
    engine = Layer3Firewall.create_dynamic(
        name=name,
        interface_id=0,
        dynamic_index=1,
        default_nat=False,
        location_ref=location_helper(location))
    
    itf = engine.routing.get(0)
    for network in itf:
        routing_node = network.data['routing_node'][0]
        routing_node['dynamic_classid'] = 'gateway'
        network.update()
    
    # License and Save Initial Configuration
    node = engine.nodes[0]
    node.bind_license()
    return node.initial_contact(as_base64=True)
    
    
def provision_stonesoft_policy(engine_policy):
    
    policy = FirewallPolicy.get_or_create(
        name=engine_policy)
        
    task = policy.upload(namespace.resource_group)
    for percentage in task.wait(timeout=5):
        logger.info('Stonesoft NGFW Policy upload task: {}%'.format(percentage))

    if not task.success:
        logger.error(task.last_message)


def azure_credentials():
    
    try:  # ServicePrincipalCredentials first
        credentials = ServicePrincipalCredentials(
            client_id=os.environ['AZURE_CLIENT_ID'],
            secret=os.environ['AZURE_CLIENT_SECRET'],
            tenant=os.environ['AZURE_TENANT_ID'])
    except KeyError:
        credentials = UserPassCredentials(
            username=os.environ['AZURE_USERNAME'],
            password=os.environ['AZURE_PASSWORD'])
    
    return credentials


def client():
    
    credentials = azure_credentials()

    return ResourceManagementClient(
        credentials,
        subscription_id)
    

def create(namespace):

    if namespace.template_path:
        with open(namespace.template_path, 'r') as template_file_fd:
            template = json.load(template_file_fd)

    pub_ssh_key_path = os.path.expanduser('~/.ssh/id_rsa.pub') # the path to rsa public key file
    
    with open(pub_ssh_key_path, 'r') as pub_ssh_file_fd:
        pub_ssh_key = pub_ssh_file_fd.read()

    session.login()
    if namespace.force_remove:
        try:
            Layer3Firewall(namespace.resource_group).delete()
        except ElementNotFound:
            pass

    engineCfg = provision_stonesoft(
        name=namespace.resource_group, 
        vnet=None,
        location=namespace.engine_location)

    parameters = {
        'engineCfg': engineCfg,
        'engineUsername': namespace.engine_username,
        'sshKey':  pub_ssh_key
    }
    parameters = {k: {'value': v} for k, v in parameters.items()}
    
    resource_client = client()
    
    resource_group_params = {
        'location': namespace.location_id,
        'tags': {'stonesoft': namespace.tag_value}
    }

    try:
        resource_client.resource_groups.create_or_update(
            namespace.resource_group,
            resource_group_params)
                                               
        deployment_properties = {
            'mode': DeploymentMode.incremental,
            'parameters': parameters,
            'template': None,
            'template_link': None
        }

        if namespace.template_path:
            deployment_properties.update(
                template=template)
        else:
            deployment_properties.update(
                template_link=TemplateLink(namespace.template_link))
        
        deployment_async_operation = resource_client.deployments.create_or_update(
            resource_group_name=namespace.resource_group,
            deployment_name=namespace.deployment_name,
            properties=deployment_properties
        )   # AzureOperationPoller
        
        initial_result = deployment_async_operation.result(timeout=30)
        
        logger.info('Starting Azure deployment; correlation id: %s',
            initial_result.properties.correlation_id)
       
        logger.info('Azure provisioning state: %s',
            initial_result.properties.provisioning_state)

        while not deployment_async_operation.done():
            deployment_async_operation.wait(timeout=30)
            
            status = resource_client.deployments.get(
                namespace.resource_group,
                deployment_name=namespace.deployment_name)
            
            logger.info('Azure provisioning state: %s',
                status.properties.provisioning_state)
    
        result = deployment_async_operation.result() 
        
        elapsed_time = result.properties.timestamp - initial_result.properties.timestamp
        logger.info('Elapsed Time: %s (seconds)', elapsed_time.total_seconds())
        
        if namespace.engine_policy:
            provision_stonesoft_policy(namespace.engine_policy)
    
        for k, v in result.properties.outputs.items():
            logger.info('{} -> {}'.format(k, v.get('value')))
             
    except CloudError:
        Layer3Firewall(
            namespace.resource_group).delete()
        raise
    finally:
        session.logout()


def destroy(namespace):

    resource_client = client()
    if resource_client.resource_groups.check_existence(namespace.resource_group):
        poller = resource_client.resource_groups.delete(  # AzureOperationPoller
            namespace.resource_group)
        session.login()
        try:
            Layer3Firewall(namespace.resource_group).delete()
        except (ElementNotFound, DeleteElementFailed) as e:
            logger.error('Problem deleting engine: {}'.format(e))
        session.logout()
        return poller.result(timeout=10)


def list_deployed(namespace):

    if namespace.all:
        query = None
    
    elif namespace.by_tag:
        query = "tagname eq '%s'" % namespace.by_tag
    
    elif namespace.resources_by_group:
        pages = resource_client.resources.list_by_resource_group(
            namespace.resources_by_group)
        for page in pages:
            print(page.name, page.type, page.location)
        return
    
    elif namespace.all_locations:
        subclient = SubscriptionClient(
            azure_credentials())
        locations = subclient.subscriptions.list_locations(subscription_id)
        print([location.name for location in locations])
        return
    
    resource_client = client()
    pages = resource_client.resource_groups.list(filter=query)
    for page in pages:
        print(page.name, page.location, page.managed_by)

        
if __name__ == '__main__':
    
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(name)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    parser = argparse.ArgumentParser(description='Stonesoft Azure Deployer')
    parser.add_argument('--quiet_logging', action='store_true', help='Disable any logging')
    
    subparsers = parser.add_subparsers()
    parser_create = subparsers.add_parser('create', help='Create NGFW resources')
    template = parser_create.add_mutually_exclusive_group(required=True)
    template.add_argument('--template_path', nargs='?', help='Path to Azure template')
    template.add_argument('--template_link', nargs='?', help='URL of Azure template')
    required = parser_create.add_argument_group('Required template parameters')
    required.add_argument('--engine_username', required=True, help='Engine username for SSH access')
    required.add_argument('--resource_group', required=True, help='Azure resource group')
    parser_create.add_argument('--location_id', nargs='?', default='westus', help='Azure Location id')
    parser_create.add_argument('--deployment_name', nargs='?', default='ngfw_azure_deployment', help='Azure deployment name')
    parser_create.add_argument('--tag_value', nargs='?', default='smc-python', help='Azure tag value for the NGFW instance')
    parser_create.add_argument('--engine_policy', nargs='?', default='_Azure_Default', help='Engine policy to assign')
    parser_create.add_argument('--engine_location', nargs='?', default=None, help='Engine location (if SMC is behind NAT)')
    parser_create.add_argument('--force_remove', action='store_true', help='Force remove NGFW if it exists')
    parser_create.set_defaults(func=create)
    
    parser_destroy = subparsers.add_parser('destroy', help='Remove NGFW resources')
    parser_destroy.add_argument('-r', '--resource_group', required=True, help='Resource group to remove')
    parser_destroy.set_defaults(func=destroy)
    
    parser_list = subparsers.add_parser('list', help='List NGFW resources')
    options = parser_list.add_mutually_exclusive_group(required=True)
    options.add_argument('-t', '--by_tag', nargs='?', const='stonesoft', help='List resources with specific tag')
    options.add_argument('-a', '--all', action='store_true', help='List all resources regardless of tag')
    options.add_argument('-g', '--resources_by_group', nargs='?', help='List all resources in a resource group')
    options.add_argument('-l', '--all_locations', action='store_true', help='List all resources in a resource group')
    parser_list.set_defaults(func=list_deployed)

    namespace = parser.parse_args()
    
    if not any(vars(namespace).values()):
        parser.print_help()
        parser.exit()

    if namespace.quiet_logging:
        logger.setLevel(logging.CRITICAL)
    
    try:
        azure_credentials()
    except KeyError:
        raise Exception(
            'Unable to find the Azure credentials within the users environment. '
            'See documentation for more info.')
    else:
        namespace.func(namespace)
