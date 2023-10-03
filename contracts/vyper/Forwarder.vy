interface ContractToDeploy:
    def setup(owner: address): nonpayable


event Log:
    addr: address


@external
def deploy(_masterCopy: address, owner: address):
    addr: address = create_minimal_proxy_to(_masterCopy)
    ContractToDeploy(addr).setup(owner)
    log Log(addr)


@external
def deployTest(_masterCopy: address):
    addr: address = create_minimal_proxy_to(_masterCopy)
    ContractToDeploy(addr).setup(self)
    log Log(addr)