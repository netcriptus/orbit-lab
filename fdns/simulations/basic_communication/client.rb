defApplication('client', 'client') do |a|

  a.path = "/basic_communication/client.py"
  a.appPackage = "http://www.inf.ufpr.br/albini/basic_communication.tar"
  a.version(1, 1, 3)
  a.shortDescription = "Programmable traffic generator v2"

  # Define the properties that can be configured for this application
  # 
  # syntax: defProperty(name = :mandatory, description = nil, parameter = nil, options = {})
  #
  a.defProperty('generator', 'Type of packet generator to use (cbr or expo)', '-g', {:type => :string, :dynamic => false})
  a.defProperty('udp:broadcast', 'Broadcast', '--udp:broadcast', {:type => :integer, :dynamic => false})
  a.defProperty('udp:dst_host', 'IP address of the Destination', '--udp:dst_host', {:type => :string, :dynamic => false})
  a.defProperty('udp:dst_port', 'Destination Port to send to', '--udp:dst_port', {:type => :integer, :dynamic => false})
  a.defProperty('udp:local_host', 'IP address of this Source node', '--udp:local_host', {:type => :string, :dynamic => false})
  a.defProperty('udp:local_port', 'Local Port of this source node', '--udp:local_port', {:type => :integer, :dynamic => false})
  a.defProperty("cbr:size", "Size of packet [bytes]", '--cbr:size', {:dynamic => true, :type => :integer})
    a.defProperty("cbr:rate", "Data rate of the flow [kbps]", '--cbr:rate', {:dynamic => true, :type => :integer})
    a.defProperty("exp:size", "Size of packet [bytes]", '--exp:size', {:dynamic => true, :type => :integer})
    a.defProperty("exp:rate", "Data rate of the flow [kbps]", '--exp:rate', {:dynamic => true, :type => :integer})
    a.defProperty("exp:ontime", "Average length of burst [msec]", '--exp:ontime', {:dynamic => true, :type => :integer})
    a.defProperty("exp:offtime", "Average length of idle time [msec]", '--exp:offtime', {:dynamic => true, :type => :integer})


    # Define the Measurement Points and associated metrics that are available for this application
    #
    a.defMeasurement('udp_out') do |m|
      m.defMetric('ts',:float)
      m.defMetric('flow_id',:long)
      m.defMetric('seq_no',:long)
      m.defMetric('pkt_length',:long)
      m.defMetric('dst_host',:string)
      m.defMetric('dst_port',:long)
    end

  end
  