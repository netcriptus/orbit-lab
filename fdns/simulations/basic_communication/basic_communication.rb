#
# Tutorial experiment
#
defProperty('duration', 30, "Duration of the experiment")

baseTopo = Topology['system:topo:imaged']

st = defTopology("sender") do |t|
  t.addNode(baseTopo.getNodeByIndex(0))
end

rt = defTopology("receiver") do |t|
  t.addNode(baseTopo.getNodeByIndex(1))
end
 
defGroup('Sender', "sender") do |node|
  node.addApplication("client.py") do |app|
    app.setProperty('udp:local_host', '192.168.0.2')
    app.setProperty('udp:dst_host', '192.168.0.3')
    app.setProperty('udp:dst_port', 5000)
    app.measure('udp_out', :samples => 1)
  end
  node.net.w1.mode = "adhoc"
  node.net.w1.type = 'g'
  node.net.w1.channel = "6"
  node.net.w1.essid = "helloworld"
  node.net.w1.ip = "192.168.0.2"
end

defGroup('Receiver', "receiver") do |node|
  node.addApplication("server.py") do |app|
    app.setProperty('udp:local_host', '192.168.0.3')
    app.setProperty('udp:local_port', 5000)
    app.measure('udp_in', :samples => 1)
  end
  node.net.w1.mode = "adhoc"
  node.net.w1.type = 'g'
  node.net.w1.channel = "6"
  node.net.w1.essid = "helloworld"
  node.net.w1.ip = "192.168.0.3"
end

onEvent(:ALL_UP_AND_INSTALLED) do |event|
  info "This is my first OMF experiment"
  wait 15
  nodes('receiver').startApplications
  wait 10
  nodes('sender').startApplications
  info "All my Applications are started now..."
  wait property.duration
  allGroups.stopApplications
  info "All my Applications are stopped now."
  Experiment.done
end