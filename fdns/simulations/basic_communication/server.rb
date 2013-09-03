defApplication('server', 'server') do |a|

  a.path = "/home/fernandocezar/Orbit/fdns/simulations/basic_communication/server.py"
  a.version(1, 1, 3)
  a.shortDescription = "Programmable traffic generator v2"
  a.description = <<TEXT
This is a test server for basic communication. It echoes what it receives.
TEXT

  # Define the properties that can be configured for this application
  # 
  # syntax: defProperty(name, description, parameter, options = nil)
  #
  a.defProperty('udp:local_host', 'IP address of this Destination node', '--udp:local_host', {:type => :string, :dynamic => false})
  a.defProperty('udp:local_port', 'Receiving Port of this Destination node', '--udp:local_port', {:type => :integer, :dynamic => false})

  # Define the Measurement Points and associated metrics that are available for this application
  #
  a.defMeasurement('udp_in') do |m|
    m.defMetric('ts',:float)
    m.defMetric('flow_id',:long)
    m.defMetric('seq_no',:long)
    m.defMetric('pkt_length',:long)
    m.defMetric('dst_host',:string)
    m.defMetric('dst_port',:long)
  end
end