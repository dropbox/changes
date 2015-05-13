import uuid

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import backref, relationship

from changes.config import db
from changes.db.types.guid import GUID
from changes.db.types.json import JSONEncodedDict
from changes.db.utils import model_repr


class Cluster(db.Model):
    """
    A group of nodes. We refer to clusters in the step configurations
    (where should we run our tests?) Clusters are automatically
    added when we see them from jenkins results.

    Apparently, clusters are only used in jenkins (not lxc, although
    nodes are used for both.) A cluster does not correspond to one master

    """
    __tablename__ = 'cluster'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128), unique=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    plans = association_proxy('cluster_nodes', 'node')

    __repr__ = model_repr('label')


class ClusterNode(db.Model):
    """
    Which cluster does each node belong to? This is populated
    at the same time as cluster.
    """
    __tablename__ = 'cluster_node'

    cluster_id = Column(GUID, ForeignKey('cluster.id', ondelete="CASCADE"),
                        nullable=False, primary_key=True)
    node_id = Column(GUID, ForeignKey('node.id', ondelete="CASCADE"),
                     nullable=False, primary_key=True)
    date_created = Column(DateTime, default=datetime.utcnow)

    cluster = relationship('Cluster', backref=backref(
        "cluster_nodes", cascade="all, delete-orphan"))
    node = relationship('Node', backref=backref(
        "node_clusters", cascade="all, delete-orphan"))

    def __init__(self, cluster=None, node=None, **kwargs):
        kwargs.setdefault('cluster', cluster)
        kwargs.setdefault('node', node)
        super(ClusterNode, self).__init__(**kwargs)


class Node(db.Model):
    """
    A machine that runs jobsteps.

    This is populated by observing the machines picked by the
    jenkins masters (which themselves are configured by BuildStep
    params in the changes UI) when they're asked to run task, and
    is not configured manually. Node machines have tags (not stored
    in the changes db)
    """
    __tablename__ = 'node'

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    label = Column(String(128), unique=True)
    data = Column(JSONEncodedDict)
    date_created = Column(DateTime, default=datetime.utcnow)

    clusters = association_proxy('node_clusters', 'cluster')

    __repr__ = model_repr('label')

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)
        if not self.id:
            self.id = uuid.uuid4()
