variable "server_type" {
  type = string
}

variable "location" {
  type    = string
  default = "hel1"
}

variable "run_number" {
  type = string
}

variable "dockerhub_org_name" {
  type = string
}

variable "use_real_price" {
  type    = number
  default = 0
}

variable "branch" {
  type = string
}


variable "proxy_model_commit" {
  type = string
}

variable "proxy_image_tag" {
  type = string
}

variable "neon_evm_commit" {
  type = string
}

variable "devnet_solana_url" {
  type = string
}

variable "faucet_model_commit" {
  type = string
}