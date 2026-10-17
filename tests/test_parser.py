from app.services.parser import parse_line


def test_parse_apache():
    line = "[Sun Dec 04 04:47:44 2005] [error] mod_jk child workerEnv in error state 6"
    parsed = parse_line(line, "Loghub-Apache")
    assert parsed["severity"] == "ERROR"
    assert parsed["service"] == "apache-server"
    assert "error state" in parsed["message"]


def test_parse_hdfs():
    line = "081109 203615 148 INFO dfs.DataNode$PacketResponder: PacketResponder 1 for block blk_388 terminating"
    parsed = parse_line(line, "Loghub-HDFS")
    assert parsed["severity"] == "INFO"
    assert parsed["service"].startswith("hdfs-")
    assert parsed["event_type"] == "termination"
