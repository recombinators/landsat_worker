import sys
sys.path.append('../landsat-util/landsat')
import pytest
import render_1
import models
from sqlalchemy import create_engine, orm
from datetime import datetime
import mock
import unittest
import os
import factory
import factory.alchemy

Session = orm.scoped_session(orm.sessionmaker())


class JobFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = models.UserJob_Model

        sqlalchemy_session = Session

    jobstatus = 0
    starttime = datetime.utcnow()
    lastmodified = datetime.utcnow()
    band1 = u'4'
    band2 = u'3'
    band3 = u'2'
    entityid = u'LC80470272015005LGN00'
    email = u'test@test.com'
    jobid = factory.Sequence(lambda n: n)


@pytest.fixture(scope='session')
def connection(request):
    engine = create_engine('postgresql://postgres@/test_bar')
    models.Base.metadata.create_all(engine)
    connection = engine.connect()
    models.DBSession.registry.clear()
    models.DBSession.configure(bind=connection)
    models.Base.metadata.bind = engine
    request.addfinalizer(models.Base.metadata.drop_all)
    return connection


@pytest.fixture
def db_session(request, connection):
    from transaction import abort
    trans = connection.begin()
    request.addfinalizer(trans.rollback)
    request.addfinalizer(abort)

    from models import DBSession
    return DBSession


@pytest.fixture(scope='class')
def fake_job1(db_session):
    model_instance = models.UserJob_Model(
        jobstatus=0,
        starttime=datetime.utcnow(),
        lastmodified=datetime.utcnow()
    )
    db_session.add(model_instance)
    db_session.flush()


#@pytest.mark.usefixtures("db_session")
#class BaseTest(object):
#    def setup_method(self, method):
#        self.config = testing.setUp()
#
#    def teardown_method(self, method):
#        transaction.abort()
#        testing.tearDown
#
# --- test db functionality tests


def test_db_lookup(db_session):
    model_instance = models.UserJob_Model(jobstatus=0,
                                          starttime=datetime.utcnow(),
                                          lastmodified=datetime.utcnow())
    db_session.add(model_instance)
    db_session.flush()

    assert 1 == db_session.query(models.UserJob_Model).count()


def test_db_is_rolled_back(db_session):
    assert 0 == db_session.query(models.UserJob_Model).count()


# --- process tests

@pytest.mark.usefixtures("connection")
@pytest.mark.usefixtures("db_session")
class TestProcess(unittest.TestCase):

    fake_job_message = {u'job_id': u'1',
                        u'band_2': u'3',
                        u'band_3': u'2',
                        u'band_1': u'4',
                        u'scene_id': u'LC80470272015005LGN00',
                        u'email': u'test@test.com'}

    def setUp(self):
        self.session = Session

    #@mock.patch('recombinators_landsat.landsat_worker.render_1.b')
    def test_download_returns_correct_values(self):
        input_path, bands, scene_id = (render_1.download_and_set(
            self.fake_job_message, render_1.PATH_DOWNLOAD))
        self.assertEqual(input_path,
                         os.getcwd() + '/download/LC80470272015005LGN00')
        self.assertEqual(bands, [u'4', u'3', u'2'])
        self.assertEqual(scene_id, 'LC80470272015005LGN00')

    #@mock.patch('recombinators_landsat.landsat_worker.render_1.b')
    def test_download_updates_job_status(self):
        input_path, bands, scene_id = (render_1.download_and_set(
            self.fake_job_message, render_1.PATH_DOWNLOAD))
        job_f = JobFactory()
        models.UserJob_Model.set_job_status(job_f.jobid, 1)
        self.assertEqual(
            [job_f], self.session.query(models.UserJob_Model).all()
        )
        self.session.commit()

    def tearDown(self):
        self.session.rollback()
        Session.remove()
