from .User.api import *
from .ClimbingLocation.api import *
from .Wall.api import *
from .SprayWall.api import *
from .FCMManager.api import *
from .settings import app
from .ranking.api import *
from .paiement.api import *
from .news.api import *
from .Partenaires.api import *
from .contest.api import *
from .Season_Pass.api import *
from .Season_Pass.Quetes.quotidien import *
from .Season_Pass.Quetes.api import *
from .gameDesign.avatar import *
from .gameDesign.baniere import *
from .gameDesign.coins import *
from .Utils.api import *
from .Wall.projet import *
from .VSL.api import *
from .fallbacks import *
from .qrcode.api import *
from .Teams.api import *
from .TeamContest.api import *
from .Stats.api import *

#add app
@app.get("/apple-app-site-association")
async def get_aasa():
    return FileResponse("static/apple-app-site-association")


@app.get("/.well-known/assetlinks.json")
async def get_aasa():
    return FileResponse("static/assetlinks.json")


@app.get('/app-ads.txt')
async def get_app_adds():
    return FileResponse("static/app-ads.txt")