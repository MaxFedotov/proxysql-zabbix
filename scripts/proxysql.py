#!/usr/bin/python2.7
import sys
import json
import mysql.connector
import argparse
import ConfigParser

#constants
proxysql_host = "127.0.0.1"
proxysql_port = 6032
conf_file     = "/var/lib/zabbix/.my.cnf"

class proxysql:
        def __init__(self, proxysql_host, proxysql_port, proxysql_user, proxysql_password):
                self.connection = mysql.connector.connect(host=proxysql_host, port=proxysql_port, user=proxysql_user, passwd=proxysql_password, db="stats")
                self.cursor = self.connection.cursor(dictionary=True)

        def __del__(self):
                self.connection.close()

        def __printf(self, str):
            print str

        def __query(self, sql):
                self.cursor.execute(sql)
                return self.cursor.fetchall()

        def get_connection_pool(self, args):
                data = self.__query("""SELECT %s
                                       FROM stats_mysql_connection_pool
                                       WHERE srv_host = "%s" and srv_port = "%s";""" % (args.param,args.host, args.port))[0]
                return (self.__printf(data[args.param]))

        def discover_mysql_servers(self,args):
                servers = {"data": []}
                data = self.__query("""SELECT DISTINCT srv_host as `{#SERVERNAME}`,
                                                       srv_port as `{#SERVERPORT}`
                                       FROM stats_mysql_connection_pool;""")
                for d in data:
                        servers["data"].append(d)
                return (self.__printf(json.dumps(servers, indent=2, sort_keys=True)))

        def discover_mysql_users(self, args):
                users = {"data": []}
                data = self.__query("""SELECT username as `{#USERNAME}`
                                       FROM stats_mysql_users
                                       GROUP BY username;""")
                for d in data:
                        users["data"].append(d)
                return (self.__printf(json.dumps(users, indent=2, sort_keys=True)))


        def get_proxysql_cluster(self, args):
                data = self.__query("""SELECT CAST(COUNT(DISTINCT(checksum)) AS INT) as checksum
                                       FROM stats_proxysql_servers_checksums
                                       WHERE name in ("%s");""" % (args.param))[0]
                return (self.__printf(data["checksum"]))

        def get_mysql_users_stats(self, args):
                data = self.__query("""SELECT %s
                                       FROM stats_mysql_users
                                       WHERE username = "%s";""" % (args.param, args.username))[0]
                return (self.__printf(data[args.param]))

        def get_global_variables(self, args):
                data = self.__query("""SELECT Variable_Value
                                       FROM stats_mysql_global
                                       WHERE Variable_Name = '%s';""" % (args.param))[0]
                return (self.__printf(data["Variable_Value"]))

config = ConfigParser.ConfigParser()
config.readfp(open(conf_file))
proxysql_user = config.get('client', 'user')
proxysql_password = config.get('client', 'password')

pcon = proxysql(proxysql_host, proxysql_port, proxysql_user, proxysql_password)
parser = argparse.ArgumentParser(prog="proxysql")
subparsers = parser.add_subparsers(help="Action to be done")

get_group = subparsers.add_parser("get")
discover_group = subparsers.add_parser("discover")

subparsers = get_group.add_subparsers()
get_pools = subparsers.add_parser("pool", help="get metrics from stats.stats_mysql_connection_pool")
get_pools.add_argument("host")
get_pools.add_argument("port")
get_pools.add_argument("param", choices=["status", "ConnUsed", "ConnFree", "ConnOK", "ConnERR", "Latency_us"])
get_pools.set_defaults(func=pcon.get_connection_pool)

get_variables = subparsers.add_parser("variable", help="get metrics from stats.stats_mysql_global")
get_variables.add_argument("param", choices=["Client_Connections_aborted","Client_Connections_connected", "Client_Connections_created", "Server_Connections_aborted",
"Server_Connections_connected", "Server_Connections_created", "Server_Connections_delayed","Client_Connections_non_idle", "Slow_queries",
"ConnPool_get_conn_immediate","ConnPool_get_conn_success","ConnPool_get_conn_failure"])
get_variables.set_defaults(func=pcon.get_global_variables)

get_users = subparsers.add_parser("user", help="get metrics from stats.stats_mysql_users")
get_users.add_argument("username")
get_users.add_argument("param", choices=["frontend_connections", "frontend_max_connections"])
get_users.set_defaults(func=pcon.get_mysql_users_stats)

get_clusters = subparsers.add_parser("cluster", help="get SUM(DISTINCT(CHECKSUM)) metric from stats.stats_proxysql_servers_checksums")
get_clusters.add_argument("param", choices=["mysql_query_rules", "mysql_servers", "mysql_users", "proxysql_servers"])
get_clusters.set_defaults(func=pcon.get_proxysql_cluster)

subparsers = discover_group.add_subparsers()
discover_servers = subparsers.add_parser("servers")
discover_servers.set_defaults(func=pcon.discover_mysql_servers)
discover_users = subparsers.add_parser("users")
discover_users.set_defaults(func=pcon.discover_mysql_users)


args = parser.parse_args()
args.func(args)