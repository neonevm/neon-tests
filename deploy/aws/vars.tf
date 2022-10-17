// AWS specific
variable "allow_list" {
  type = list(string)
}

variable "solana_instance_type" {
  type = string
}

variable "proxy_instance_type" {
  type = string
}

variable "ami" {
  type = string
}

// software specific
variable "branch" {
  type = string
  default = "develop"
}


variable "proxy_container_tag" {
  type = string
  default = "latest"
}


variable "neon_evm_container_tag" {
  type = string
  default = "latest"
}


variable "faucet_container_tag" {
  type = string
  default = "latest"
}
