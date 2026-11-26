"""No adapter is installed. Capabilities must be verified by the actual host."""
def available(capabilities,name):
    return type(capabilities) is dict and type(name) is str and capabilities.get(name) is True
