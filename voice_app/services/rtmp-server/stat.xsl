<?xml version="1.0" encoding="utf-8" ?>
<!--
  NGINX-RTMP Statistics XSL Stylesheet
  Provides a clean, responsive interface for viewing stream statistics
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="html"/>

<xsl:template match="/">
<html>
<head>
    <title>RTMP Server Statistics</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        
        .header .subtitle {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .content {
            padding: 30px;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #667eea;
        }
        
        .stat-card h3 {
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 1.2em;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #667eea;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .stream-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .stream-table th {
            background: #667eea;
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 500;
        }
        
        .stream-table td {
            padding: 12px 10px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .stream-table tr:hover {
            background: #f8f9fa;
        }
        
        .status-live {
            color: #28a745;
            font-weight: bold;
        }
        
        .status-idle {
            color: #6c757d;
        }
        
        .timestamp {
            text-align: center;
            color: #6c757d;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
        }
        
        .no-data {
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 40px;
        }
        
        @media (max-width: 768px) {
            .stat-grid {
                grid-template-columns: 1fr;
            }
            
            .stream-table {
                font-size: 0.9em;
            }
            
            .stream-table th,
            .stream-table td {
                padding: 8px 6px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 RTMP Server Statistics</h1>
            <div class="subtitle">Real-time Voice Streaming Platform</div>
        </div>
        
        <div class="content">
            <!-- Server Statistics -->
            <div class="stat-grid">
                <div class="stat-card">
                    <h3>Server Uptime</h3>
                    <div class="stat-value"><xsl:value-of select="rtmp/uptime div 1000"/></div>
                    <div class="stat-label">seconds</div>
                </div>
                
                <div class="stat-card">
                    <h3>Total Connections</h3>
                    <div class="stat-value"><xsl:value-of select="rtmp/naccepted"/></div>
                    <div class="stat-label">accepted</div>
                </div>
                
                <div class="stat-card">
                    <h3>Bandwidth In</h3>
                    <div class="stat-value"><xsl:value-of select="format-number(rtmp/bw_in div 1024, '#,##0')"/></div>
                    <div class="stat-label">KB/s</div>
                </div>
                
                <div class="stat-card">
                    <h3>Bandwidth Out</h3>
                    <div class="stat-value"><xsl:value-of select="format-number(rtmp/bw_out div 1024, '#,##0')"/></div>
                    <div class="stat-label">KB/s</div>
                </div>
            </div>
            
            <!-- Live Streams -->
            <div class="section">
                <h2>🔴 Live Streams</h2>
                <xsl:choose>
                    <xsl:when test="rtmp/server/application/live">
                        <table class="stream-table">
                            <thead>
                                <tr>
                                    <th>Stream Name</th>
                                    <th>Publisher</th>
                                    <th>Viewers</th>
                                    <th>Bandwidth In</th>
                                    <th>Bandwidth Out</th>
                                    <th>Duration</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <xsl:for-each select="rtmp/server/application[name='live']/live/stream">
                                    <tr>
                                        <td><strong><xsl:value-of select="name"/></strong></td>
                                        <td>
                                            <xsl:choose>
                                                <xsl:when test="publishing">
                                                    <xsl:value-of select="publishing/remote_addr"/>
                                                </xsl:when>
                                                <xsl:otherwise>-</xsl:otherwise>
                                            </xsl:choose>
                                        </td>
                                        <td><xsl:value-of select="count(client[publishing!=''])"/></td>
                                        <td><xsl:value-of select="format-number(bw_in div 1024, '#,##0')"/> KB/s</td>
                                        <td><xsl:value-of select="format-number(bw_out div 1024, '#,##0')"/> KB/s</td>
                                        <td><xsl:value-of select="format-number(time div 1000, '#,##0')"/>s</td>
                                        <td>
                                            <xsl:choose>
                                                <xsl:when test="publishing">
                                                    <span class="status-live">● LIVE</span>
                                                </xsl:when>
                                                <xsl:otherwise>
                                                    <span class="status-idle">○ IDLE</span>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                        </td>
                                    </tr>
                                </xsl:for-each>
                            </tbody>
                        </table>
                    </xsl:when>
                    <xsl:otherwise>
                        <div class="no-data">No live streams currently active</div>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Voice Streams -->
            <div class="section">
                <h2>🎤 Voice Streams</h2>
                <xsl:choose>
                    <xsl:when test="rtmp/server/application[name='voice']/live">
                        <table class="stream-table">
                            <thead>
                                <tr>
                                    <th>Stream Name</th>
                                    <th>Publisher</th>
                                    <th>Listeners</th>
                                    <th>Audio Bitrate</th>
                                    <th>Duration</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <xsl:for-each select="rtmp/server/application[name='voice']/live/stream">
                                    <tr>
                                        <td><strong><xsl:value-of select="name"/></strong></td>
                                        <td>
                                            <xsl:choose>
                                                <xsl:when test="publishing">
                                                    <xsl:value-of select="publishing/remote_addr"/>
                                                </xsl:when>
                                                <xsl:otherwise>-</xsl:otherwise>
                                            </xsl:choose>
                                        </td>
                                        <td><xsl:value-of select="count(client[publishing!=''])"/></td>
                                        <td><xsl:value-of select="format-number(bw_in div 1024, '#,##0')"/> KB/s</td>
                                        <td><xsl:value-of select="format-number(time div 1000, '#,##0')"/>s</td>
                                        <td>
                                            <xsl:choose>
                                                <xsl:when test="publishing">
                                                    <span class="status-live">● LIVE</span>
                                                </xsl:when>
                                                <xsl:otherwise>
                                                    <span class="status-idle">○ IDLE</span>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                        </td>
                                    </tr>
                                </xsl:for-each>
                            </tbody>
                        </table>
                    </xsl:when>
                    <xsl:otherwise>
                        <div class="no-data">No voice streams currently active</div>
                    </xsl:otherwise>
                </xsl:choose>
            </div>
            
            <!-- Applications Overview -->
            <div class="section">
                <h2>📡 Applications</h2>
                <table class="stream-table">
                    <thead>
                        <tr>
                            <th>Application</th>
                            <th>Active Streams</th>
                            <th>Total Connections</th>
                            <th>Bandwidth In</th>
                            <th>Bandwidth Out</th>
                        </tr>
                    </thead>
                    <tbody>
                        <xsl:for-each select="rtmp/server/application">
                            <tr>
                                <td><strong><xsl:value-of select="name"/></strong></td>
                                <td><xsl:value-of select="count(live/stream[publishing])"/></td>
                                <td><xsl:value-of select="count(.//client)"/></td>
                                <td><xsl:value-of select="format-number(sum(.//bw_in) div 1024, '#,##0')"/> KB/s</td>
                                <td><xsl:value-of select="format-number(sum(.//bw_out) div 1024, '#,##0')"/> KB/s</td>
                            </tr>
                        </xsl:for-each>
                    </tbody>
                </table>
            </div>
            
            <div class="timestamp">
                Last updated: <script>document.write(new Date().toLocaleString());</script>
                <br/>
                <a href="?" style="color: #667eea; text-decoration: none;">🔄 Refresh</a>
            </div>
        </div>
    </div>
</body>
</html>
</xsl:template>

</xsl:stylesheet> 