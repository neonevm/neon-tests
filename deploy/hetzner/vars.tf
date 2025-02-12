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