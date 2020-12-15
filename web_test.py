from requests_html import HTMLSession
import urllib3
import json
from bs4 import BeautifulSoup
# import pyppeteer
# import pyppdf.patch_pyppeteer
# import pyppeteer.chromium_downloader as pypc
#
# pypc.download_chromium()



website = '''
b'<html>\n  <head>\n    <title>Cisco vManage</title>\n    <link rel="stylesheet" type="text/css" href="/login.css">\n    
<link rel="stylesheet" type="text/css" href="/fonts/font-awesome-4.2.0/css/font-awesome.min.css">\n        
<link rel="stylesheet" type="text/css" href="/bootstrap.min.css">\n        <script type="text/javascript" 
src="/javascript/jquery.js"></script>\n        <link rel="icon" type="image/ico" href="/images/favicon.ico"/>\n    
<script>\n      var count = 1, max = 30;\n      function init(){\n        var rebootBlock = 
document.getElementById(\'reboot_message\');\n        rebootBlock.style.display = "none";\n        var loginBlock = 
document.getElementById(\'login_message\');\n        loginBlock.style.display = "block";\n        
checkServerStatus();\n      }\n      function checkServerStatus() {\n        if(count <= max){\n          
var xhr = new XMLHttpRequest();\n          xhr.open("GET", "/dataservice/client/server/ready", true);\n          
xhr.onload = function (e) {\n            if (xhr.readyState === 4) {\n              if (xhr.status === 200) {\n                
var rebootBlock = document.getElementById(\'reboot_message\');\n                rebootBlock.style.display = "none";\n                
var loginBlock = document.getElementById(\'login_message\');\n                loginBlock.style.display = "block";\n              
} else {\n                var rebootBlock = document.getElementById(\'reboot_message\');\n                
rebootBlock.style.display = "block";\n                var loginBlock = document.getElementById(\'login_message\');\n                
loginBlock.style.display = "none";\n                count++;\n                setTimeout(checkServerStatus, 10000);\n              
}\n            }\n          };\n          xhr.onerror = function (e) {\n            count++;\n            
setTimeout(checkServerStatus, 10000);\n          };\n          xhr.send(null);\n        }else{\n          var 
rebootBlock = document.getElementById(\'reboot_message\');\n          rebootBlock.style.display = "none";\n          
var loginBlock = document.getElementById(\'login_message\');\n          loginBlock.style.display = "block";\n        
}\n      }\n      function validateForm() {\n        if(loginForm.j_username.value.length==0 || 
loginForm.j_username.value=="")\n        {\n          showErrorMessage("Invalid Username.");\n          
document.getElementById("j_username").className="login-input-error";\n          return false;\n        } else 
if(loginForm.j_password.value.length == 0 || loginForm.j_password.value=="")\n        {\n          
showErrorMessage("Invalid Password.")\n          document.getElementById("j_password").className="login-input-error";\n
return false;\n        } else {\n          hideErrorMessage();\n          return true;\n        }\n      
}\n\n      function showErrorMessage(msg) {\n        document.getElementById("errorMessageBox").innerHTML=msg;
          \n      };\n\n      function hideErrorMessage() {\n        document.getElementById("errorMessageBox").
          innerHTML=\' \';\n        document.getElementById("j_username").className="login-input-value";\n        
          document.getElementById("j_password").className="login-input-value";\n      }\n    </script>\n  </head>\n  
          <body onload="init()">\n      <div name="Login" class="loginContainer">\n      
          <div class="loginInnerContainer">\n        <div class="productCategory">Cisco SD-WAN</div>\n        
          <form class="loginFormStyle" name="loginForm" id="loginForm" method="POST" 
          action="j_security_check" onsubmit="return validateForm()" autocomplete="off">\n          
          <div name="logoMainContainer"  class="logoMainContainer"></div>\n          
          <div class="brand-logo-text"><span>Cisco vManage</span></div>\n          <p id="errorMessageBox" 
name="errorMessageBox" class=\'errorMessageBox \'></p>\n          <div id="reboot_message" class="reboot-message-block">
\n            <div class="reboot-message">Server is initializing. Please wait.</div>\n            
<i class="fa fa-circle-o-notch fa-spin fa-3x fa-fw"></i>\n          </div>\n          <div id="login_message" 
style="display: none;">\n            <div class=\'onyx-groupbox login-wrap\' name="inputFields">\n              
<div class="onyx-input-decorator login-input">\n                <input type="text" class="login-input-value"  
size="18"\n                     id="j_username" name="j_username" maxlength="64" placeholder="Username" value="" 
onfocus="hideErrorMessage()" autofocus />\n              </div>\n              <div class="onyx-input-decorator 
login-input">\n                <input type="password" class="login-input-value"  size="18"\n                     
id="j_password" name="j_password" placeholder="Password"  value="" onfocus="hideErrorMessage()" />\n              
</div>\n            </div>\n            <div class=\'onyx-sample-tools login-wrap\'>\n              <input type="submit"  
name="submit"  value="Log In" class="login-button"  />\n            </div>\n          </div>\n        </form>\n      
</div>\n      </div>\n  </body>\n</html>\n'
'''

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

c = urllib3.HTTPSConnectionPool('172.28.43.174', port=8443, cert_reqs='CERT_NONE')

source = c.request('GET', '/#/app/administration/settings')


#
# http = urllib3.PoolManager()
# source = http.request('GET', 'https://172.28.43.174:8443')

soup = BeautifulSoup(source, "html5lib")
#
# title of the page
print(soup.title)

# get attributes:
# print(soup.title.name)

# get values:
# print(soup.title.string)

# beginning navigation:
# print(soup.title.parent.name)

# getting specific values:
print(soup.p)

forms = soup.find_all('<form>')
print(forms)

session = HTMLSession(verify=False)
#
r = session.get('https://172.28.43.174:8443/#/app/administration/settings')
#
render = r.html.render()
#
r.html.search('Python 2 will retire in only {months} months!')['months']