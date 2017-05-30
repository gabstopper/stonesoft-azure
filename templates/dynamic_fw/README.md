<a href="https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fgabstopper%2Fstonesoft-azure%2Fmaster%2Ftemplates%2Fdynamic_fw%2Fazuredeploy.json" target="_blank">
    <img src="http://azuredeploy.net/deploybutton.png"/>
</a>
<a href="http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fgabstopper%2Fstonesoft-azure%2Fmaster%2F/templates/dynamic_fw/azuredeploy.json" target="_blank">
    <img src="http://armviz.io/visualizebutton.png"/>
</a>

Template used to deploy Stonesoft NGFW to Microsoft Azure with a single leg DHCP interface that is internet facing. Running the installation using stonesoft-azure will create the NGFW within the Stonesoft SMC automatically and auto-provision a specified
policy.

To install, follow the instructions for running ``stonesoft_azure.py``.

At a minimum when launching these templates, you will need to specify the ``--engine_username``, ``--resource_group`` and have an SSH public key available in your home directory (~/.ssh/id_rsa.pub).

If your Stonesoft Management Center is behind NAT, you will want to create a 'Location' element and assign the public IP address where the SMC is reachable. 

Use the ``--engine_location`` parameter to specify the name of the Location and the NGFW will be placed in this location and know where to reach the SMC.

```
(venv351) python stonesoft_azure.py create \
    --engine_username dlepage \
    --resource_group dlepage-rg \
    --engine_location='Internet' \
    --template_link=https://raw.githubusercontent.com/gabstopper/stonesoft-azure/master/templates/dynamic_fw/azuredeploy.json \
    --location_id westeurope \
```  

Once complete, SSH will work to the public address of the NGFW (make sure you have a rule allowing SSH).

ssh user@{stonesoft_azure_fw}




