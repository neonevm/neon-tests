
resource "hcloud_server" "proxy" {
  name        = "proxy-${var.run_number}-${var.branch}"
  image       = data.hcloud_image.ci-image.id
  server_type = var.server_type
  location    = var.location
  ssh_keys = [
    data.hcloud_ssh_key.ci-ssh-key.id
  ]

  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }

  network {
    network_id = data.hcloud_network.ci-network.id
  }

  labels = {
    environment = "ci"
    purpose     = "ci-oz-full-tests"
  }
  depends_on = [
    hcloud_server.solana
  ]
}


resource "null_resource" "proxy_provision" {
  depends_on = [hcloud_server.proxy]
  triggers = {
      proxy_srv_id = hcloud_server.proxy.id
  }

  provisioner "file" {
    content     = data.template_file.proxy_init.rendered
    destination = "/tmp/proxy_init.sh"

    connection {
      type        = "ssh"
      user        = "root"
      host        = hcloud_server.proxy.ipv4_address
      private_key = file("/tmp/ci-stands")
    }

  }

}

resource "hcloud_server" "solana" {
  name        = "solana-${var.run_number}-${var.branch}"
  image       = data.hcloud_image.ci-image.id
  server_type = var.server_type
  location    = var.location
  ssh_keys = [
    data.hcloud_ssh_key.ci-ssh-key.id
  ]

  public_net {
    ipv4_enabled = true
    ipv6_enabled = false
  }

  network {
    network_id = data.hcloud_network.ci-network.id
  }

  labels = {
    environment = "ci"
  }
}


resource "null_resource" "solana_provision" {
  depends_on = [hcloud_server.solana]
  triggers = {
    solana_srv_id = hcloud_server.solana.id
  }

    provisioner "file" {
    content     = data.template_file.solana_init.rendered
    destination = "/tmp/solana_init.sh"

    connection {
      type        = "ssh"
      user        = "root"
      host        = hcloud_server.solana.ipv4_address
      private_key = file("/tmp/ci-stands")
    }

  }
}
