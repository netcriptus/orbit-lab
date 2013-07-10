# -*- mode: ruby -*-
# vi: set ft=ruby :

cwd_name = File.basename(File.dirname(__FILE__))

Vagrant.configure("2") do |config|
  config.vm.box = "precise64"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"

  config.vm.synced_folder ".", "/#{cwd_name}"

  config.vm.provision :shell, :inline => "gem install chef --version 11.4.2 --no-rdoc --no-ri --conservative"

  config.vm.provision :chef_solo do |chef|
    chef.cookbooks_path = ["site-cookbooks", "cookbooks"]

    chef.add_recipe "fdns"

    chef.json = { :pip_requirements => ["/#{cwd_name}/requirements.txt"] }
  end
end