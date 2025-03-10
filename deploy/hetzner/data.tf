data "hcloud_image" "ci-image" {
  name              = "ubuntu-22.04"
  with_architecture = "x86"
}

data "hcloud_network" "ci-network" {
  name = "ci-network"
}

data "hcloud_ssh_key" "ci-ssh-key" {
  name = "hcloud-ci-stands"
}

data "template_file" "solana_init" {
  template = file("solana_init.sh")

  vars = {
    branch              = var.branch
    proxy_model_commit  = var.proxy_model_commit
    proxy_image_tag     = var.proxy_image_tag
    neon_evm_commit     = var.neon_evm_commit
    faucet_model_commit = var.faucet_model_commit
    dockerhub_org_name  = var.dockerhub_org_name
    devnet_solana_url   = var.devnet_solana_url
  }
}

data "template_file" "proxy_init" {
  template = file("proxy_init.sh")

  vars = {
    branch              = var.branch
    proxy_model_commit  = var.proxy_model_commit
    proxy_image_tag     = var.proxy_image_tag
    solana_ip           = hcloud_server.solana.network.*.ip[0]
    neon_evm_commit     = var.neon_evm_commit
    faucet_model_commit = var.faucet_model_commit
    dockerhub_org_name  = var.dockerhub_org_name
    use_real_price      = var.use_real_price
    devnet_solana_url   = var.devnet_solana_url
  }
}
