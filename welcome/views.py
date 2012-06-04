import re
import tornado
import pymongo
import meteor


class WelcomeView(meteor.core.View):
    url = '/'

    def get(self):
        r = re.compile('^([0-9\.]+)[0-9a-z]*$')

        self.render_view('index.html',
            tornado_version=tornado.version,
            meteor_version=meteor.version, pymongo_version=pymongo.version,
            pymongo_version_href = r.match(pymongo.version).groups()[0],

            packages=self.application.package_manager.packages,
            settings=self.application.settings,
            databases=self.application.databases,
            metadata=self.application.views_metadata
        )

    def embedded_js(self):
        return '''
        meteor.onReady(function() {
            new MeteorEvent({
                name: "meteor.welcome/test",
                data: {'test': true},
                callback: function(data) {
                    if (data.test) {
                        $(".ws_test").text('WebSockets works correctly !!!')
                    }
                }
            })
        });
        '''

    def embedded_css(self):
        return '''
        body {
            padding: 0px; margin: 0px; font-family:
            Lucida Grande,arial,verdana,sans-serif,Lucida Sans;
        }
        h1 {text-align:center; text-shadow: grey 2px 2px 3px;}
        a {text-decoration: none; color: #000;}
        a:hover {text-decoration: underline; color: #000;}

        table {
            width: 1000px; border: 1px solid; margin-top: 15px;
            margin-bottom: 25px;
        }
        td {width: 50%; border: 1px solid; padding: 2px;}

        .header_row {
            background: #ffde7a; text-align: center; font-size: 14pt;
            font-weight: bold; text-shadow: grey 2px 2px 3px;
        }
        .ws_test {font-style: italic; text-shadow: grey 2px 2px 3px;}
        '''

    def metadata(self):
        return {'title': 'New Meteor Application'}
