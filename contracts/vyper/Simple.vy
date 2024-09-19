owner: public(address)

# Define ZERO_ADDRESS constant
ZERO_ADDRESS_CONST: constant(address) = 0x0000000000000000000000000000000000000000

# __init__ is not called when deployed from create_forwarder_to
@deploy
def __init__():
  self.owner = msg.sender

# call once after create_forwarder_to
@external
def setup(owner: address):
  assert self.owner == ZERO_ADDRESS_CONST, "owner != zero address"
  self.owner = owner


# DANGER: never have selfdestruct in original contract used by create_forwarder_to
@external
def kill():
  selfdestruct(msg.sender)