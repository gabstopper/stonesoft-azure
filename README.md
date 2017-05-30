### Stonesoft Azure Deployer

Features:

 * Auto deploy and provision Stonesoft FW in Azure and SMC
 * Provisioning from on box templates
 * Provisioning from remote template locations

#### Installation

1. Setup virtualenv:

    ```
    virtualenv -p /usr/local/bin/python3.5 venv351
    . venv/bin/activate
    ```

2. Clone the repository and install:

    ```
    git clone https://github.com/gabstopper/stonesoft-azure.git
    cd stonesoft-azure
    ```
    
    Install all required libraries within the virtual environment:

    ```
    pip install -r requirements.txt
    ```

3. Create environment variables with the necessary IDs for Azure authentication. You can use either ServiceCredentials or UserCredentials.
	
	If using ServiceCredentials, set the following environment variables:

	```
	export AZURE_TENANT_ID={your Azure Active Directory tenant id or domain}
	export AZURE_CLIENT_ID={your Azure Active Directory Application Client ID}
	export AZURE_CLIENT_SECRET={your Azure Active Directory Application Secret}
	```
	
	If using UserCredentials, set the following environment variables:
	
	```
	export AZURE_USERNAME={my_username}
	export AZURE_PASSWORD={my_password}
	export AZURE_SUBSCRIPTION_ID={subscription_id}
	```
	
	ServiceCredentials are tried first, then fall back to UserCredentials.
	
	For more information on Azure authentication, see: [Resource Management Authentication](http://azure-sdk-for-python.readthedocs.io/en/latest/quickstart_authentication.html#).
	
4. Set Stonesoft SMC credential environment variables:

    The deployer requires smc-python to interface with the SMC in order to automate the layer 3 firewall creation. There are multiple ways to provide credentials for smc-python, for more information, see smc-python: [creating the session](http://smc-python.readthedocs.io/en/latest/pages/session.html).

    For simplicity, set the following environment variables for the SMC server and client API Key:

    ```
    export SMC_API_KEY={key_generated_for_my_api_client}
    export SMC_ADDRESS={http://10.10.10.10}
    ```

5. Generate your public SSH key:

    Your machine will need an SSH public key when creating the deployment to enable remote access to the NGFW and clients. The script will look for the public key in ``~/.ssh/id_rsa.pub``. This key will be used in the parameters template to deploy to the virtual machine/s.

    For more information on creaging Azure keys, see: [Microsoft Azure documentation](https://docs.microsoft.com/en-us/azure/virtual-machines/linux/mac-create-ssh-keys?toc=azurevirtual-machineslinuxtoc.json).

    For Mac/Linux it's as easy as:

    ```
    ssh-keygen -t rsa -b 2048
    chmod 400 ~/.ssh/id_rsa.pub
    ```

#### Running the deployer

To run the deployer, execute stonesoft-azure.py.

Top level commands specify the action (list, create, destroy). Each top level command may have required
switches as well. Use the help option to display the menus.

Example commands for creating:

```
(venv351) $ python stonesoft_azure.py create -h
usage: stonesoft_azure.py create [-h]
                                 (--template_path [TEMPLATE_PATH] | --template_link [TEMPLATE_LINK])
                                 --engine_username ENGINE_USERNAME
                                 --resource_group RESOURCE_GROUP
                                 [--location_id [LOCATION_ID]]
                                 [--deployment_name [DEPLOYMENT_NAME]]
                                 [--tag_value [TAG_VALUE]]
                                 [--engine_policy [ENGINE_POLICY]]
                                 [--engine_location [ENGINE_LOCATION]]
                                 [--force_remove]

optional arguments:
  -h, --help            show this help message and exit
  --template_path [TEMPLATE_PATH]
                        Path to Azure template
  --template_link [TEMPLATE_LINK]
                        URL of Azure template
  --location_id [LOCATION_ID]
                        Azure Location id
  --deployment_name [DEPLOYMENT_NAME]
                        Azure deployment name
  --tag_value [TAG_VALUE]
                        Azure tag value for the NGFW instance
  --engine_policy [ENGINE_POLICY]
                        Engine policy to assign
  --engine_location [ENGINE_LOCATION]
                        Engine location (if SMC is behind NAT)
  --force_remove        Force remove NGFW if it exists

Required template parameters:
  --engine_username ENGINE_USERNAME
                        Engine username for SSH access
  --resource_group RESOURCE_GROUP
                        Azure resource group
           
```

You must provide either ``--template_path`` or ``--template_link``. In addition, there are other optional settings available to customize the NGFW configuration within the SMC, such as setting an engine location, (if SMC is behind NAT), policy to assign, 

##### Deploy using template on local system:

If you cloned the repository, you will find common templates in the /templates directory. To use these, or other ones on your local system, use ``--template_path`` when calling the script:

```
(venv351) python stonesoft_azure.py \
    --engine_username dlepage \
    --resource_group dlepage-rg \
    --engine_location='Internet' \
    --template_path=templates/engine.json \
    --location_id westeurope \
    --force_remove
```

##### Deploy using template on remote site:

You can also deploy templates that are located in a remote location accessible by http or https. To use these, use ``--template_link`` when calling the script:

```
(venv351) python stonesoft_azure.py \
    --engine_username dlepage \
    --resource_group dlepage-rg \
    --engine_location='Internet' \
    --template_link=https://raw.githubusercontent.com/azuredeploy.json \
    --location_id westeurope \
    --force_remove
```

There are a variety of templates that can be used to meet common use cases stored in the templates/ directory. These are also cross linked to the Azure Portal.
